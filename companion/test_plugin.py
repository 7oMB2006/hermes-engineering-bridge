import asyncio
import importlib.util
import json
import sys
import socket
import threading
import time
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

root = Path(__file__).parent
spec = importlib.util.spec_from_file_location('dfsc_plugin_fixture', root/'__init__.py', submodule_search_locations=[str(root)])
plugin = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = plugin
spec.loader.exec_module(plugin)

class PluginTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ctx = NS(_manager=NS(has_gateway_message_injector=False))
        self.integration = plugin.Integration(self.ctx, Path(self.temp.name), {'FEISHU_ALLOWED_USERS':'owner', 'FEISHU_APP_ID':'bot'}, plugin.CompanionConfig('fixture-agent', 'Fixture', Path(self.temp.name)))
        self.sent=[]
        self.integration.send=lambda chat,message:self.sent.append((chat,message))
        self.integration.close_cards=lambda *args:None
    def tearDown(self):
        self.integration.stop()
        self.temp.cleanup()
    def test_presets_overrides_and_deadline(self):
        self.assertEqual(plugin.parse_allowance('过夜推进')['preset'],'overnight')
        self.assertEqual(plugin.parse_allowance('给你四小时，最多返工十轮')['limitMs'],4*3600000)
        self.assertEqual(plugin.parse_allowance('给你四小时，最多返工十轮')['maxCorrections'],10)
        self.assertIn('deadline',plugin.parse_allowance('到明早八点停'))
    def test_ambiguous_allowance_requires_clarification(self):
        for text in ['半小时左右', '截止明天中午', '跑到明早']:
            with self.assertRaises(ValueError):plugin.parse_allowance(text)
    def test_model_never_reads_human_capabilities(self):
        with patch.object(self.integration,'rpc') as rpc:
            result=json.loads(self.integration.tool({'method':'human.approval','params':{}}))
            self.assertIn('error',result)
            rpc.assert_not_called()
    def test_model_task_allowance_cannot_override_owner_grant(self):
        self.integration.state['grant']={'id':'grant'}
        with patch.object(self.integration,'rpc',return_value={}) as rpc:
            self.integration.tool({'method':'task.create','params':{'preset':'overnight','grantId':'fake','limitMs':999,'key':'x'}})
            params=rpc.call_args.args[2]
            self.assertEqual(params['grantId'],'grant')
            self.assertNotIn('limitMs',params)
            self.assertNotIn('preset',params)
    def test_typed_card_text_cannot_forge_native_card_callback(self):
        source=NS(platform=NS(value='feishu'),user_id='owner',chat_id='chat')
        event=NS(source=source,internal=False,text='/card button {"dfsc_nonce":"x"}',raw_message=None)
        with patch.object(self.integration,'rpc') as rpc:
            self.assertIsNone(asyncio.run(self.integration.inbound(event)))
            rpc.assert_not_called()
    def test_real_card_checks_operator_bot_chat_and_message(self):
        info={'taskId':'task','requestId':'approval','chatId':'chat','userId':'owner','messageId':'msg','appId':'bot','options':[{'confirmed':True}]}
        self.integration.state['cards']['nonce']=info
        def event(user='owner',bot='bot',chat='chat',msg='msg'):
            return NS(source=NS(platform=NS(value='feishu'),user_id=user,chat_id=chat),internal=False,text='/card button',raw_message=NS(header=NS(event_type='card.action.trigger',app_id=bot),event=NS(action=NS(value={'dfsc_nonce':'nonce','choice':0}),operator=NS(open_id=user),context=NS(open_chat_id=chat,open_message_id=msg))))
        for values in [('other','bot','chat','msg'),('owner','wrong','chat','msg'),('owner','bot','wrong','msg'),('owner','bot','chat','wrong')]:
            with patch.object(self.integration,'rpc') as rpc:
                asyncio.run(self.integration.inbound(event(*values)))
                rpc.assert_not_called()
        with patch.object(self.integration,'rpc',return_value={}) as rpc:
            asyncio.run(self.integration.inbound(event()))
            self.assertEqual(rpc.call_args.args[1],'human.approval')
            self.assertTrue(rpc.call_args.kwargs['human'])
    def test_plain_control_rejects_unknown_owner(self):
        event=NS(source=NS(platform=NS(value='feishu'),user_id='stranger',chat_id='chat'),internal=False,text='/dfsc extend 2h 3',raw_message=None)
        with patch.object(self.integration,'rpc') as rpc:
            result=asyncio.run(self.integration.inbound(event))
            self.assertEqual(result['action'],'skip')
            rpc.assert_not_called()
    def test_reading_task_acknowledges_wake_but_submission_does_not(self):
        self.integration.state['pendingWakes']={'1':{'taskId':'task'}}
        with patch.object(self.integration,'rpc',return_value={}):
            self.integration.tool({'method':'task.get','params':{'taskId':'task'}})
        self.assertFalse(self.integration.state['pendingWakes'])

    def test_compound_owner_return_preserves_guidance_and_continues(self):
        text='归还控制权并继续虾待办；增加重要标记，不重试被拒绝的命令。'
        event=NS(source=NS(platform=NS(value='feishu'),user_id='owner',chat_id='chat'),internal=False,text=text,raw_message=None)
        task={'id':'task','phase':'review','limitMs':1800000,'maxCorrections':1,'origin':{'chatId':'chat','sessionKey':'original-feishu-session'}}
        injected=[]
        self.ctx.inject_message=lambda content,**kw:injected.append((content,kw))
        def rpc(root,method,params=None,**kwargs):
            return [task] if method=='task.list' else task
        with patch.object(self.integration,'rpc',side_effect=rpc) as mock:
            asyncio.run(self.integration.inbound(event))
            methods=[c.args[1] for c in mock.call_args_list]
            self.assertLess(methods.index('human.control'),methods.index('human.continue'))
            control=next(c for c in mock.call_args_list if c.args[1]=='human.control')
            self.assertEqual(control.args[2]['guidance'],text)
        self.assertEqual(injected[0][1]['session_key'],'original-feishu-session')
        self.assertIn(text,injected[0][0])

    def test_reconnect_closes_stale_cards_but_keeps_current_native_request(self):
        self.integration.state['cards']={'stale':{'taskId':'paused','requestId':'old'},'live':{'taskId':'active','requestId':'current','messageId':'message'},'expired':{'taskId':'active','requestId':'expired'}}
        closed=[]
        self.integration.close_cards=lambda task,request:closed.append((task,request))
        def rpc(root,method,params):
            if method=='task.get':return {'phase':'paused' if params['taskId']=='paused' else 'waiting'}
            return {'requests':[{'id':'current'}]}
        with patch.object(self.integration,'rpc',side_effect=rpc):self.integration.reconcile_cards()
        self.assertEqual(closed,[('paused','old'),('active','expired')])

    def test_status_card_never_forwards_raw_tool_outputs(self):
        source=NS(chat_id='chat',user_id='owner')
        task={'id':'task','title':'工程','phase':'running','origin':{'chatId':'chat'},'runs':[{'tools':[{'output':'DO-NOT-FORWARD-RAW-LOG'}]}]}
        with patch.object(self.integration,'rpc',return_value=[task]):asyncio.run(self.integration.control('status',source))
        self.assertNotIn('DO-NOT-FORWARD',self.sent[-1][1])
        self.assertIn('工程',self.sent[-1][1])

    def test_projection_keeps_native_test_ids_and_excludes_reasoning(self):
        task={'runs':[{'id':'run','tools':[{'id':'native-test-id','command':'node --test','ok':True,'output':'pass 56 / fail 0'}],'summary':'done'}]}
        result=plugin.compact_snapshot({'task':task,'messages':[{'role':'assistant','content':[{'type':'thinking','thinking':'PRIVATE-REASONING'},{'type':'text','text':'finished'}]}],'requests':[]})
        self.assertEqual(result['task']['testEvidenceCandidates'][0]['toolCallId'],'native-test-id')
        self.assertIn('pass 56',result['task']['testEvidenceCandidates'][0]['output'])
        self.assertNotIn('PRIVATE-REASONING',json.dumps(result))
        self.assertEqual(result['messages'][0]['content'],'finished')

    def test_allowance_report_counts_interrupted_runs_from_ledger(self):
        task={'limitMs':1800000,'usedMs':1000,'maxCorrections':2,'runs':[{'status':'failed'},{'status':'failed'},{'status':'finished'}]}
        result=plugin.compact_task(task)
        self.assertEqual(result['correctionsUsed'],2)
        self.assertEqual(result['correctionsRemaining'],0)
        self.assertEqual(result['remainingMs'],1799000)

    def test_read_ack_cannot_swallow_an_event_arriving_during_the_query(self):
        self.integration.state['pendingWakes']={'1':{'taskId':'task'}}
        def rpc(*args,**kwargs):
            self.integration.state['pendingWakes']['2']={'taskId':'task'}
            return {}
        with patch.object(self.integration,'rpc',side_effect=rpc):
            self.integration.tool({'method':'task.get','params':{'taskId':'task'}})
        self.assertEqual(set(self.integration.state['pendingWakes']),{'2'})

    def test_failed_read_does_not_ack_wake(self):
        self.integration.state['pendingWakes']={'1':{'taskId':'task'}}
        with patch.object(self.integration,'rpc',side_effect=TimeoutError('uncertain')):
            self.integration.tool({'method':'session.snapshot','params':{'taskId':'task'}})
        self.assertEqual(set(self.integration.state['pendingWakes']),{'1'})

    def test_unknown_card_send_reuses_exact_durable_payload_and_nonce(self):
        task={'id':'task','title':'test','origin':{'chatId':'chat','userId':'owner'}}
        request={'id':'request','method':'confirm','message':'safe fixture'}
        attempts=[]
        def send(path,body):
            attempts.append(body)
            if len(attempts)==1:raise TimeoutError('accepted but reply lost')
            return {'message_id':'message'}
        self.integration.rest=send
        with self.assertRaises(TimeoutError):self.integration.card(task,request)
        disk=json.loads(self.integration.state_path.read_text())
        self.assertEqual(len(disk['cards']),1)
        self.integration.card(task,request)
        self.assertEqual(attempts[0],attempts[1])
        self.assertEqual(attempts[0]['uuid'],next(iter(disk['cards'])))
        self.integration.card(task,request)
        self.assertEqual(len(attempts),2)

    def test_card_only_offers_single_use_native_choices(self):
        self.integration.rest=lambda *args,**kw:{'message_id':'message'}
        self.integration.card({'id':'task','title':'test','origin':{'chatId':'chat','userId':'owner'}},{'id':'request','method':'select','options':['Allow once','Always allow','Remember for project','允许本次','本会话全部允许']})
        choices=next(iter(self.integration.state['cards'].values()))['options']
        self.assertEqual(choices,[{'value':'Allow once'},{'value':'允许本次'},{'cancelled':True}])

    def test_unload_joins_the_event_consumer_before_reload(self):
        self.ctx._manager.has_gateway_message_injector=True
        entered=threading.Event()
        def wait(root,method,params=None,**kwargs):
            if method=='task.list':return []
            entered.set();kwargs['cancel'].wait(5);raise RuntimeError('cancelled')
        with patch.object(self.integration,'rpc',side_effect=wait):
            self.integration.start();self.assertTrue(entered.wait(1))
            started=time.monotonic();self.integration.stop()
            self.assertLess(time.monotonic()-started,1)
            self.assertFalse(self.integration.thread.is_alive())

    @unittest.skipIf(sys.platform == 'win32' or not hasattr(socket, 'AF_UNIX'), 'Unix-only transport; loopback is covered separately')
    def test_actual_socket_read_cancels_without_waiting_for_server_reply(self):
        from importlib import import_module
        client=import_module(plugin.__name__+'.client')
        with tempfile.TemporaryDirectory(prefix='dfsc-',dir='/tmp') as directory:
            listener=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
            address=str(Path(directory)/'b.sock');listener.bind(address);listener.listen(1)
            (Path(directory)/'model.json').write_text(json.dumps({'version':1,'token':'fixture','socket':address}))
            cancel=threading.Event();errors=[]
            def run():
                try:client.call(directory,'events.wait',cancel=cancel)
                except Exception as exc:errors.append(str(exc))
            worker=threading.Thread(target=run);worker.start()
            connection,_=listener.accept();connection.recv(4096)
            started=time.monotonic();cancel.set();worker.join(1)
            connection.close();listener.close()
            self.assertFalse(worker.is_alive());self.assertLess(time.monotonic()-started,1)
            self.assertIn('cancelled',errors[0])

    def test_post_admission_uses_real_gateway_serialized_source_contract(self):
        source={'platform':'feishu','chat_id':'chat','user_id':'owner'}
        with patch.object(self.integration,'rpc',return_value={'id':'new-grant'}) as rpc:
            asyncio.run(self.integration.admitted(source=source,session_key='session',text='标准档'))
            self.assertEqual(rpc.call_args.args[1],'human.grant')
            self.assertEqual(rpc.call_args.args[2]['origin'],{'chatId':'chat','userId':'owner','sessionKey':'session'})
            self.assertTrue(rpc.call_args.kwargs['human'])
        self.assertEqual(self.integration.state['grant']['id'],'new-grant')

    def test_post_admission_unknown_or_missing_identity_never_grants(self):
        with patch.object(self.integration,'rpc') as rpc:
            for source in [None,{}, {'platform':'other','user_id':'owner','chat_id':'chat'},{'platform':'feishu','user_id':'stranger','chat_id':'chat'}]:
                asyncio.run(self.integration.admitted(source=source,text='过夜'))
            rpc.assert_not_called()

    def test_continuation_carries_new_owner_scope_into_authoritative_wake(self):
        text='继续验收；允许第三阶段，不重试被拒绝的命令。'
        event=NS(source=NS(platform=NS(value='feishu'),user_id='owner',chat_id='chat'),internal=False,text=text,raw_message=None)
        task={'id':'task','phase':'paused','limitMs':60000,'maxCorrections':2,'origin':{'chatId':'chat'}}
        def rpc(root,method,params=None,**kwargs):return [task] if method=='task.list' else task
        with patch.object(self.integration,'rpc',side_effect=rpc) as calls:
            asyncio.run(self.integration.inbound(event))
            continuation=next(c for c in calls.call_args_list if c.args[1]=='human.continue')
            self.assertEqual(continuation.args[2]['guidance'],text)
            self.assertTrue(continuation.kwargs['human'])

    def test_recovery_reads_official_owner_message_and_scopes_evidence_to_task(self):
        task={'id':'task','origin':{'source':'management-recovery','originalFeishuMessageId':'om_real','userId':'owner','chatId':'chat'}}
        message={'message_id':'om_real','sender':{'sender_type':'user','id_type':'open_id','id':'owner'},'chat_id':'chat','msg_type':'text','body':{'content':json.dumps({'text':'允许第三阶段，最多一次'})}}
        self.integration.rest=lambda path:{'items':[message]}
        with patch.object(self.integration,'rpc',return_value=task):
            record=self.integration.recover_owner_instruction('om_real','task')
            output=json.loads(self.integration.tool({'method':'task.get','params':{'taskId':'task'}}))
        self.assertEqual(output['verifiedOwnerInstruction'],record)
        self.assertEqual(record['text'],'允许第三阶段，最多一次')
        self.assertEqual(record['verification'],'feishu-official-message-readback')
        with patch.object(self.integration,'rpc',return_value={'id':'another','runs':[]}):
            other=json.loads(self.integration.tool({'method':'task.get','params':{'taskId':'another'}}))
        self.assertNotIn('verifiedOwnerInstruction',other)

    def test_recovery_rejects_other_sender_chat_bot_or_unrelated_message(self):
        task={'id':'task','origin':{'source':'management-recovery','originalFeishuMessageId':'om_real','userId':'owner','chatId':'chat'}}
        base={'message_id':'om_real','sender':{'sender_type':'user','id_type':'open_id','id':'owner'},'chat_id':'chat','msg_type':'text','body':{'content':json.dumps({'text':'允许第三阶段'})}}
        for change in [{'chat_id':'wrong'},{'sender':{'sender_type':'app','id_type':'open_id','id':'owner'}},{'sender':{'sender_type':'user','id_type':'open_id','id':'other'}},{'message_id':'om_other'}]:
            self.integration.rest=lambda path,change=change:{'items':[{**base,**change}]}
            with patch.object(self.integration,'rpc',return_value=task),self.assertRaises(ValueError):
                self.integration.recover_owner_instruction('om_real','task')
        self.assertFalse(self.integration.state['verifiedOwnerInstructions'])
        with patch.object(self.integration,'rpc',return_value={'origin':{}}),self.assertRaises(ValueError):
            self.integration.recover_owner_instruction('om_real','task')

class DelegationTests(unittest.TestCase):
    setUp = PluginTests.setUp
    tearDown = PluginTests.tearDown
    def test_delegated_event_wakes_once_and_does_not_auto_answer(self):
        task={'id':'t','phase':'waiting','control':'agent','origin':{'userId':'owner','chatId':'chat','sessionKey':'original'}}
        request={'id':'q','method':'input','bridgeApproval':{'category':'questions','delegated':True}}
        wakes=[]
        self.ctx.inject_message=lambda content,session_key:wakes.append((content,session_key)) or True
        self.integration.card=lambda *args:None
        with patch.object(self.integration,'rpc',return_value={'requests':[request]}) as rpc:
            self.integration.route_approvals(task)
            self.integration.route_approvals(task)
            self.assertEqual(len(wakes),1)
            self.assertEqual(wakes[0][1],'original')
            self.assertEqual([c.args[1] for c in rpc.call_args_list],['approval.list','approval.list'])
            self.assertIn('approval:t:q',self.integration.state['pendingWakes'])
            self.integration.route_approvals({**task,'control':'human'})
            self.assertNotIn('approval:t:q',self.integration.state['pendingWakes'])
    def test_feishu_outage_does_not_block_delegated_wake(self):
        task={'id':'t','phase':'waiting','control':'agent','origin':{'userId':'owner','chatId':'chat','sessionKey':'original'}}
        request={'id':'q','method':'input','bridgeApproval':{'category':'questions','delegated':True}}
        wakes=[]
        self.ctx.inject_message=lambda *a,**k:wakes.append(a) or True
        self.integration.card=lambda *args:(_ for _ in ()).throw(RuntimeError('offline'))
        with patch.object(self.integration,'rpc',return_value={'requests':[request]}):self.integration.route_approvals(task)
        self.assertEqual(len(wakes),1)
    def test_questionnaire_card_has_native_option_buttons_and_readable_question(self):
        task={'id':'t','title':'test','origin':{'userId':'owner','chatId':'chat'}}
        request={'id':'q','method':'input','title':'Desktop clarification\n{}','bridgeApproval':{'questions':[{'id':'q','label':'依赖','question':'Install pytest?','allowFreeform':True,'options':[{'label':'批准安装','value':'authorize_pytest'}]}]}}
        sent=[]
        self.integration.rest=lambda path,body:sent.append(body) or {'message_id':'msg'}
        self.integration.card(task,request)
        card=json.loads(sent[0]['content'])
        self.assertNotIn('Desktop clarification',card['elements'][0]['text']['content'])
        self.assertIn('Install pytest?',card['elements'][0]['text']['content'])
        self.assertEqual(next(iter(self.integration.state['cards'].values()))['options'][0],{'value':'authorize_pytest'})
    def test_delegated_tool_has_no_human_setting_authority(self):
        with patch.object(self.integration,'rpc',return_value={'resolved':True}) as rpc:
            self.assertTrue(json.loads(self.integration.tool({'method':'approval.respond','params':{'taskId':'t','requestId':'q','reason':'test','value':'A'}}))['resolved'])
            self.assertFalse(rpc.call_args.kwargs.get('human',False))
        with patch.object(self.integration,'rpc') as rpc:
            self.assertIn('error',json.loads(self.integration.tool({'method':'human.delegation','params':{'policy':{}}})))
            rpc.assert_not_called()

    def test_reading_task_does_not_ack_unanswered_native_request(self):
        self.integration.state['pendingWakes']={
            'approval:t:q':{'taskId':'t'},'run-finished':{'taskId':'t'}}
        with patch.object(self.integration,'rpc',return_value={}):
            self.integration.tool({'method':'task.get','params':{'taskId':'t'}})
        self.assertIn('approval:t:q',self.integration.state['pendingWakes'])
        self.assertNotIn('run-finished',self.integration.state['pendingWakes'])

    def test_retention_reconciles_current_state_without_replaying_deleted_events(self):
        self.integration.state['pendingWakes']={'old':{'taskId':'deleted'},'current':{'taskId':'keep'}}
        self.integration.state['verifiedOwnerInstructions']={'deleted':{'text':'old'},'keep':{'text':'current'}}
        self.integration.state['cards']={'old':{'taskId':'deleted'},'current':{'taskId':'keep'}}
        tasks=[{'id':'keep','phase':'waiting'}]
        routed=[]
        self.integration.route_approvals=lambda task:routed.append(task['id'])
        with patch.object(self.integration,'rpc',return_value=tasks) as rpc:
            self.integration.reconcile_retention(2)
        self.assertEqual(self.integration.state['historyGeneration'],2)
        self.assertEqual(list(self.integration.state['pendingWakes']),['current'])
        self.assertEqual(list(self.integration.state['cards']),['current'])
        self.assertEqual(list(self.integration.state['verifiedOwnerInstructions']),['keep'])
        self.assertEqual(routed,['keep'])
        self.assertEqual(rpc.call_args.args[1],'task.list')
    def test_retention_reconciliation_pages_all_retained_task_metadata(self):
        self.integration.state['pendingWakes']={'last':{'taskId':'last'}}
        self.integration.route_approvals=lambda task:None
        page=[{'id':str(i),'phase':'accepted'} for i in range(50)]
        with patch.object(self.integration,'rpc',side_effect=[page,[{'id':'last','phase':'paused'}]]) as rpc:
            self.integration.reconcile_retention(3)
        self.assertEqual(rpc.call_args_list[1].args[2],{'offset':50})
        self.assertIn('last',self.integration.state['pendingWakes'])

    def test_archive_tools_are_narrow_capabilities_without_human_credentials(self):
        for method in ['session.archiveStatus','session.archive','session.restore']:
            with patch.object(self.integration,'rpc',return_value={'archived':True}) as rpc:
                result=json.loads(self.integration.tool({'method':method,'params':{'taskId':'owned'}}))
                self.assertTrue(result['archived'])
                self.assertEqual(rpc.call_args.args[2],{'taskId':'owned'})
                self.assertFalse(rpc.call_args.kwargs.get('human',False))
        with patch.object(self.integration,'rpc') as rpc:
            self.assertIn('error',json.loads(self.integration.tool({'method':'session.delete','params':{'sessionId':'other'}})))
            rpc.assert_not_called()

if __name__=='__main__':unittest.main()
