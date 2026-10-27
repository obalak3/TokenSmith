// Production PR source packing; direct local inference with identical fixed settings.
import { readFileSync, writeFileSync, existsSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { createHash, randomBytes } from 'node:crypto'
import { parseArgs } from 'node:util'

const out=dirname(fileURLToPath(import.meta.url));
const repo=resolve(out,'../../..');
const {values}=parseArgs({options:{source:{type:'string'}}});
if(!values.source) throw new Error('--source is required');
process.chdir(resolve(values.source));
const {requireTranspiledTs}=await import(pathToFileURL(resolve(out,'ts-module-loader.mjs')));
const {prepareStudyChatMessages,answerWithOrderedSources}=requireTranspiledTs('src/main/engine/study-chat-format.ts');
const read=name=>JSON.parse(readFileSync(resolve(out,name),'utf8'));
const write=(name,value)=>writeFileSync(resolve(out,name),JSON.stringify(value,null,2)+'\n');
const K=Number(process.env.K||8);
const TAG=process.env.TAG; if(!TAG) throw new Error('TAG required');
const ARMS=(process.env.ARMS||'off,on').split(',');
const OUT='answers-ext-'+TAG+'-k'+K+'.json';
const cases=read('cases-ext.json');
const retrieval=read('retrieval-ext-'+TAG+'.json');
const model={id:'ollama:gemma4:e4b',name:'gemma4:e4b',engine:'ollama',role:'generator',status:'ready',
  ollamaModelName:'gemma4:e4b',ollamaBaseUrl:'http://127.0.0.1:11434',contextLength:8192};
const modelSettings={contextLengthMode:'manual',contextLength:8192,maxLength:1024,temperature:0,
  topP:1,topK:40,minP:0,repeatPenalty:1.1,reasoningMode:'off',thinking:false,
  systemMessage:'Answer the student in at most 180 words. Address each requested part using the supplied course sources. If those sources do not support a needed detail, say so; do not invent it.'};
const outputs=existsSync(resolve(out,OUT))?read(OUT):[];
async function call(request) {
  const start=performance.now();
  const response=await fetch('http://127.0.0.1:11434/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify(request),signal:AbortSignal.timeout(180000)});
  if(!response.ok)throw new Error('Ollama '+response.status+' '+await response.text());
  return {request,response:await response.json(),seconds:(performance.now()-start)/1000};
}
for(let i=0;i<cases.length;i++) {
  const c=cases[i];
  for(const arm of (i%2?['on','off']:['off','on']).filter(a=>ARMS.includes(a))) {
    if(outputs.some(o=>o.id===c.id&&o.arm===arm))continue;
    const start=performance.now();const calls=[];
    const retrieved=retrieval.find(r=>r.id===c.id&&r.arm===arm&&r.mode==='hybrid'&&r.k===K).result.sources;
    let request={prompt:c.question,messages:[],materials:[],settings:{},model,modelSettings,
      applicationSettings:{suggestionMode:'off'},retrievedSources:retrieved};
    let prepared;
    try {
      for(;;) {
        prepared=prepareStudyChatMessages(request);
        const apiRequest={model:'gemma4:e4b',messages:prepared.messages,stream:false,think:false,
          options:{num_ctx:8192,num_predict:1,temperature:0,top_p:1,top_k:40,min_p:0,repeat_penalty:1.1,seed:157}};
        const probe=await call(apiRequest);calls.push({...probe,phase:'preflight'});
        const count=probe.response.prompt_eval_count;
        if(!Number.isInteger(count)||count<=0)throw new Error('Missing token count');
        if(count+prepared.budget.answerReserveTokens+prepared.budget.safetyMarginTokens<=8192)break;
        if(prepared.sources.length<=1)throw new Error('No room for a complete answer');
        request={...request,retrievedSources:prepared.sources.slice(0,-1)};
      }
      const apiRequest={...calls.at(-1).request,options:{...calls.at(-1).request.options,num_predict:1024}};
      const completion=await call(apiRequest);calls.push({...completion,phase:'answer'});
      if(completion.response.done_reason==='length')throw new Error('Answer reached output limit');
      const raw=completion.response.message?.content?.trim();
      if(!raw)throw new Error('Empty answer');
      const answer=answerWithOrderedSources(raw,prepared.sources);
      outputs.push({id:c.id,concept:c.concept,arm,question:c.question,answer:answer.text,
        sources:prepared.sources,budget:prepared.budget,calls,seconds:(performance.now()-start)/1000});
      console.log('ANSWER',i+1,'/',cases.length,arm,(performance.now()-start).toFixed(0)+'ms');
    }catch(error) {
      outputs.push({id:c.id,concept:c.concept,arm,question:c.question,error:String(error),
        sources:prepared?.sources,budget:prepared?.budget,calls,seconds:(performance.now()-start)/1000});
      console.error('ANSWER ERROR',c.id,arm,String(error));
    }
    write(OUT,outputs);
  }
}
console.log('DONE '+OUT);
