'use strict';
// Strict grammar for bounded owner/agent workflow dispatch.
const FILENAME = /^[a-z0-9][a-z0-9_-]{0,100}\.ya?ml$/;
const INPUT_NAME = /^[a-z][a-z0-9_]{0,50}$/;
const INPUT_VALUE = /^[A-Za-z0-9_.:,/@+-]{1,120}$/;
function allowedWorkflow(filename) {
  if (!FILENAME.test(filename)) return false;
  if (/maintenance|prune|publish|owner-comment|owner-command|dispatcher|bootstrap/.test(filename)) return false;
  return /^(issue[0-9]+-[a-z0-9_-]+|s2[a-z0-9-]*|s3[a-z0-9-]*|science-[a-z0-9-]*|docker-portable)\.ya?ml$/.test(filename);
}
function parseDispatchRequest(body) {
  if (typeof body !== 'string' || body.length > 1500) throw Error('DISPATCH_BODY_INVALID');
  if (body.includes('\n') || body.includes('\r')) throw Error('DISPATCH_SINGLE_LINE_REQUIRED');
  const fields = body.trim().split(/\s+/);
  if (fields.length < 3 || fields.length > 13 ||
      fields[0] !== '/cteas' || fields[1] !== 'run')
    throw Error('DISPATCH_SYNTAX_EXPECTED');
  const workflow = fields[2];
  if (!allowedWorkflow(workflow)) throw Error('DISPATCH_WORKFLOW_NOT_APPROVED');
  const inputs = {};
  for (const item of fields.slice(3)) {
    const delimiter = item.indexOf('=');
    if (delimiter <= 0) throw Error('DISPATCH_INPUT_MUST_BE_KEY_VALUE');
    const key = item.slice(0, delimiter), value = item.slice(delimiter + 1);
    if (!INPUT_NAME.test(key) || !INPUT_VALUE.test(value) ||
        Object.prototype.hasOwnProperty.call(inputs, key))
      throw Error('DISPATCH_INPUT_INVALID_OR_DUPLICATE');
    inputs[key] = value;
  }
  return {workflow, inputs};
}
function authorizedIssueComment(payload, repository) {
  const comment=payload && payload.comment, issue=payload && payload.issue;
  return repository === 'RRain001/CTEAS-next' && !!comment &&
    comment.user?.login === 'RRain001' &&
    comment.author_association === 'OWNER' &&
    !!issue && issue.state === 'open' && !issue.pull_request;
}
module.exports={allowedWorkflow,parseDispatchRequest,authorizedIssueComment};
