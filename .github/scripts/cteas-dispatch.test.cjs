'use strict';
const test=require('node:test'), assert=require('node:assert/strict');
const {parseDispatchRequest,allowedWorkflow,authorizedIssueComment}=require('./cteas-dispatch.cjs');
const context={comment:{user:{login:'RRain001'},author_association:'OWNER'},issue:{number:123,state:'open'}};
test('owner comment only; reject PR, closed issue or outside repo',()=>{
 assert.equal(authorizedIssueComment(context,'RRain001/CTEAS-next'),true);
 assert.equal(authorizedIssueComment({...context,comment:{...context.comment,user:{login:'outsider'}}},'RRain001/CTEAS-next'),false);
 assert.equal(authorizedIssueComment({...context,comment:{...context.comment,author_association:'NONE'}},'RRain001/CTEAS-next'),false);
 assert.equal(authorizedIssueComment({...context,issue:{...context.issue,pull_request:{url:'x'}}},'RRain001/CTEAS-next'),false);
 assert.equal(authorizedIssueComment({...context,issue:{...context.issue,state:'closed'}},'RRain001/CTEAS-next'),false);
 assert.equal(authorizedIssueComment(context,'some/other'),false);
});
test('parse default and explicit input trigger commands',()=>{
 assert.deepEqual(parseDispatchRequest('/cteas run issue123-original-binary-full-manual.yml'),{workflow:'issue123-original-binary-full-manual.yml',inputs:{}});
 assert.deepEqual(parseDispatchRequest('/cteas run issue119-wolsong-p2b-real-coast.yml validation_scope=full_p2b'),{workflow:'issue119-wolsong-p2b-real-coast.yml',inputs:{validation_scope:'full_p2b'}});
 assert.deepEqual(parseDispatchRequest('/cteas run issue84-noaa-source-screen.yml years=2023,2024 max_nearest=6'),{workflow:'issue84-noaa-source-screen.yml',inputs:{years:'2023,2024',max_nearest:'6'}});
});
test('unsafe workflows are excluded',()=>{
 for(const name of ['maintenance-prune-branches.yml','issue53-gshhg-publish-project-release.yml','issue54-owner-comment-dispatch.yml','ubuntu-bootstrap.yml','science-dispatcher.yml','../science-c1-143h.yml'])assert.equal(allowedWorkflow(name),false,name);
 assert.equal(allowedWorkflow('science-c1-143h.yml'),true);
 assert.equal(allowedWorkflow('s2c-issue25-all-fresh-143h.yml'),true);
});
test('reject injection, duplicate input and multiline',()=>{
 for(const cmd of ['/cteas run ../science-c1-143h.yml','/cteas run science-c1-143h.yml ref=experimental;rm','/cteas run science-c1-143h.yml A=1','/cteas run science-c1-143h.yml x=one x=two','/cteas run science-c1-143h.yml x=$SECRET','/cteas run science-c1-143h.yml\nanother-command','/cteas run maintenance-prune-branches.yml','/cteas run science-c1-143h.yml x="a b"'])
   assert.throws(()=>parseDispatchRequest(cmd),undefined,cmd);
});
