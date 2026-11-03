const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname,'../dashboard/dist/index.js'),'utf8');

function harness(row, windowExtra={}) {
  let component, cursor=0, firstEffect=true;
  const states=[], calls=[];
  const React={
    Fragment:'fragment',
    createElement:(tag,props,...children)=>({tag,props:props||{},children}),
    useState:(initial)=>{const i=cursor++;if (!(i in states)) states[i]=initial;return [states[i],v=>{states[i]=v;}];},
    useEffect:fn=>{if(firstEffect){firstEffect=false;fn();}}
  };
  const sdk={React,fetchJSON:async(url,options)=>{
    calls.push([url,options]);
    if(options) row={...row,status:JSON.parse(options.body).choice,choice:JSON.parse(options.body).choice};
    return row;
  }};
  vm.runInNewContext(source,{window:{__HERMES_PLUGIN_SDK__:sdk,__HERMES_PLUGINS__:{register:(name,fn)=>{component=fn;}},location:{search:'?request=r1'},...windowExtra},
    URLSearchParams,Date,setInterval:()=>1,clearInterval:()=>{}});
  return {calls,render:()=>{cursor=0;return component();}};
}
function find(tree,tag) {
  if(!tree||typeof tree!=='object') return [];
  return [...(tree.tag===tag?[tree]:[]),...tree.children.flatMap(child=>find(child,tag))];
}
const pending=()=>({id:'r1',digest:'d',command:'<script>bad()</script>',description:'Test',expires:Date.now()/1000+60,status:'pending',choice:null});

test('two exclusive decision buttons, safe command text and bound POST',async()=>{
  const h=harness(pending()); h.render(); await new Promise(setImmediate);
  let tree=h.render(); const buttons=find(tree,'button');
  assert.deepEqual(buttons.map(b=>b.children[0]),['Approve once','Deny']);
  assert.equal(find(tree,'input').length,0);
  const pre=find(tree,'pre')[0]; assert.equal(pre.children[0],'<script>bad()</script>');
  assert.equal(pre.props.dangerouslySetInnerHTML,undefined);
  buttons[0].props.onClick(); await new Promise(setImmediate); tree=h.render();
  assert.ok(find(tree,'button').every(b=>b.props.disabled));
  const post=h.calls.find(c=>c[1]);
  assert.equal(post[0],'/api/plugins/approval-link/requests/r1/decision');
  assert.deepEqual(JSON.parse(post[1].body),{digest:'d',choice:'once'});
});

test('expired cards cannot send a decision',async()=>{
  const h=harness({...pending(),expires:Date.now()/1000-1}); h.render(); await new Promise(setImmediate);
  const buttons=find(h.render(),'button'); assert.ok(buttons.every(b=>b.props.disabled));
  buttons[0].props.onClick(); await new Promise(setImmediate);
  assert.equal(h.calls.filter(c=>c[1]).length,0);
});

test('a framed page renders no buttons and fetches nothing',async()=>{
  const h=harness(pending(),{top:{},self:{}}); const tree=h.render(); await new Promise(setImmediate);
  assert.equal(find(tree,'button').length,0);
  assert.equal(h.calls.length,0);
});
