import {test} from 'node:test';
import assert from 'node:assert/strict';
import {chromium} from 'playwright';
import {execFileSync} from 'node:child_process';
import {readFile, mkdir} from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'..');
execFileSync(process.env.PYTHON || 'python',[path.join(root,'tests/make_fixture.py')],{cwd:root});
const fragment=await readFile(path.join(root,'artifacts/round.html'),'utf8');
const browser=await chromium.launch({headless:true,...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{})});
process.on('exit',()=>void browser.close());
async function page(mode='success',width=390){
  const p=await browser.newPage({viewport:{width,height:900}});
  await p.addInitScript(()=>{});
  await p.setContent(`<style>body{margin:16px;font:16px system-ui}.form-check{display:flex;align-items:center;min-height:44px;gap:8px}.form-control{display:block;width:100%;box-sizing:border-box;font:inherit}.btn{min-height:44px;max-width:100%;font:inherit}.viz-row{display:flex;flex-wrap:wrap;gap:8px}.form-label{display:block}fieldset{min-width:0}</style><script>window.messages=[];window.saved=[];window.openai={setWidgetState:async s=>window.saved.push(s)};if(${JSON.stringify(mode)}!=='missing')window.openai.sendFollowUpMessage=async m=>{window.messages.push(m);if(${JSON.stringify(mode)}==='failure')throw Error('Host rejected');};</script>${fragment}`);
  return p;
}
async function fill(p){await p.getByLabel('自己使用',{exact:true}).check();await p.getByLabel('计划文档',{exact:true}).check();await p.getByLabel('你的回答（也可写尚不确定）').fill('预算 100 元');}
test('320/390/1280 responsive, no default choices, questionnaire submits',async()=>{
  for(const width of [320,390,1280]){const p=await page('success',width);assert.equal(await p.locator('input:checked').count(),0);assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await fill(p);await p.getByRole('button',{name:'提交答案并继续访谈'}).click();assert.equal(await p.evaluate(()=>messages.length),1);await p.screenshot({path:path.join(root,`artifacts/questionnaire-${width}.png`),fullPage:true});await p.close();}
});
test('empty answers rejected and drafts save only private content',async()=>{const p=await page();assert.equal(await p.locator('#grill-lite-fallback').isVisible(),false);assert.equal(await p.locator('#grill-lite-checkpoint').isVisible(),false);await p.getByRole('button',{name:'提交答案并继续访谈'}).click();assert.equal(await p.evaluate(()=>messages.length),0);await fill(p);assert.equal(await p.evaluate(()=>saved.at(-1).modelContent),null);await p.close();});
test('host failure keeps answers and retries use same submission ID',async()=>{const p=await page('failure');await fill(p);await p.getByRole('button',{name:'提交答案并继续访谈'}).click();await p.getByRole('button',{name:'提交答案并继续访谈'}).click();assert.deepEqual(await p.evaluate(()=>messages.map(m=>JSON.parse(m.prompt.split('\n')[1]).submission_id)),await p.evaluate(()=>Array(2).fill(JSON.parse(messages[0].prompt.split('\n')[1]).submission_id)));assert.ok(await p.locator('#grill-lite-fallback').isVisible());await p.close();});
test('missing bridge exposes copy message without claiming delivery',async()=>{const p=await page('missing');await fill(p);await p.getByRole('button',{name:'提交答案并继续访谈'}).click();assert.match(await p.locator('#grill-lite-status').innerText(),/没有提交桥/);assert.match(await p.locator('#grill-lite-fallback').inputValue(),/^GRILL_LITE_ANSWERS_V1/);await p.close();});
test('checkpoint includes unanswered draft and import goes through host for validation',async()=>{const p=await page();await p.getByLabel('自己使用',{exact:true}).check();await p.getByRole('button',{name:'读取状态文本'}).click();const value=JSON.parse(await p.locator('#grill-lite-checkpoint').inputValue());assert.equal(value.session.draft.answers[0].selected[0],'self');assert.equal(value.session.draft.answers[2].text,'');await p.getByRole('button',{name:'导入文本读档'}).click();assert.match(await p.evaluate(()=>messages[0].prompt),/^GRILL_LITE_IMPORT_V1/);await p.close();});
test.after(async()=>{await browser.close();});
