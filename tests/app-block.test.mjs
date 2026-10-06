import {test} from 'node:test';
import assert from 'node:assert/strict';
import {chromium} from 'playwright';
import {execFileSync} from 'node:child_process';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'..');
execFileSync(process.env.PYTHON||'python',[path.join(root,'tests/make_fixture.py')],{cwd:root});
const html=await readFile(path.join(root,'artifacts/app-block.html'),'utf8');
const browser=await chromium.launch({headless:true,...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{})});
async function page(width=390){const p=await browser.newPage({viewport:{width,height:900}});await p.setContent(html);return p;}
async function fill(p){await p.getByLabel('自己使用',{exact:true}).check();await p.getByLabel('计划文档',{exact:true}).check();await p.getByLabel('你的回答').fill('预算一百元');}
async function message(p){return p.getByLabel('可复制文本').inputValue();}
test('touch widths no overflow or preselected answers; manual callback IDs stable until edits',async()=>{
  for(const w of [320,390,1280]){const p=await page(w);assert.equal(await p.locator('input:checked').count(),0);assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await fill(p);
  await p.getByRole('button',{name:'生成提交消息',exact:true}).click();const a=JSON.parse((await message(p)).split('\n')[1]);
  await p.getByRole('button',{name:'生成提交消息',exact:true}).click();assert.equal(JSON.parse((await message(p)).split('\n')[1]).submission_id,a.submission_id);
  await p.getByLabel('你的回答').fill('预算二百元');await p.getByRole('button',{name:'生成提交消息',exact:true}).click();assert.notEqual(JSON.parse((await message(p)).split('\n')[1]).submission_id,a.submission_id);
  assert.match(await p.getByRole('status').innerText(),/复制.*发送/);await p.screenshot({path:path.join(root,`artifacts/app-block-${w}.png`),fullPage:true});await p.close();}
});
test('partial draft has readable text, imports locally, rejects unrelated draft atomically',async()=>{const p=await page();await p.getByLabel('自己使用',{exact:true}).check();await p.getByRole('button',{name:'导出当前草稿',exact:true}).click();const draft=await message(p);assert.match(draft,/Grill Me Lite 草稿/);assert.match(draft,/自己使用/);
  await p.getByRole('button',{name:'清空本轮填写',exact:true}).click();assert.equal(await p.locator('input:checked').count(),0);
  await p.getByLabel('可复制文本').fill(draft);await p.getByRole('button',{name:'导入草稿 / 存档',exact:true}).click();assert.equal(await p.locator('input:checked').count(),1);
  await p.getByLabel('可复制文本').fill(draft.replace(/batch_id: .*/, 'batch_id: unrelated'));await p.getByRole('button',{name:'导入草稿 / 存档',exact:true}).click();assert.match(await p.getByRole('status').innerText(),/另一轮/);assert.equal(await p.locator('input:checked').count(),1);await p.close();});
test('checkpoint becomes manual message; broken import does not erase draft; missing answers are not unknown',async()=>{const p=await page();await p.getByRole('button',{name:'生成提交消息',exact:true}).click();assert.match(await p.getByRole('status').innerText(),/尚未回答/);
  await fill(p);await p.getByLabel('可复制文本').fill('# Grill Me Lite 存档\n等待聊天解析');await p.getByRole('button',{name:'导入草稿 / 存档',exact:true}).click();assert.match(await message(p),/^GRILL_LITE_IMPORT_V1\n# Grill/);
  await p.getByLabel('可复制文本').fill('{broken');await p.getByRole('button',{name:'导入草稿 / 存档',exact:true}).click();assert.match(await p.getByRole('status').innerText(),/聊天.*修复/);assert.equal(await p.locator('input:checked').count(),2);await p.close();});
test.after(async()=>{await browser.close();});
