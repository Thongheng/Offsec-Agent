# offsec-agent

Human guide for running a focused, authorized HackerOne hunt with the offsec
workflow.

Use this only where you have authorization. On HackerOne, the asset must be in
scope, eligible for submission, and allowed by the program policy.

## Recommended First Shape

Start with:

```text
Stored XSS through object/name fields that propagate into another user-visible
or admin-visible view.
```

Why this shape:

- easy to understand and reproduce;
- clear source -> storage -> render path;
- common across many SaaS products;
- can be tested safely with unique markers;
- easier for a first report than complex authz or exploit-heavy bugs.

Fields to look for: project name, workspace name, team name, product name,
catalog item name, display name, ticket title, organization name.

Keep proof harmless. Do not use destructive payloads or third-party
exfiltration.

## Start Prompt

Open an agent session in this repo and paste:

```text
Use the offsec workflow for authorized HackerOne testing only.

Goal: find a valid, reproducible, in-scope bug.

First shape: stored XSS through object/name fields that render in another
user-visible or admin-visible view.

Start with selection only:
- build or review a 3-5 program candidate portfolio;
- check policy, scope, and eligibility before testing;
- define a <=1h kill-test for each candidate;
- do not hunt yet;
- do not mark anything verified without replay or my explicit reproduced result.
```

If you already have program handles:

```text
Use the offsec workflow for authorized HackerOne testing only.

Candidate programs: <handle-a>, <handle-b>, <handle-c>.
Shape: stored XSS through object/name fields.

Check policy/scope/eligibility and define kill-tests first. Do not hunt yet.
```

## Your Job

You make the human decisions:

1. Choose 3-5 authorized programs.
2. Confirm account creation/testing is allowed by policy.
3. Give the agent the handles.
4. During kill-test, sign up/log in and confirm whether the product has
   user-controlled name/title fields that render elsewhere.
5. Pick one target and one enabled feature.
6. Create safe test data with a unique marker.
7. Reproduce any candidate before it is marked verified.
8. Submit only if the bug is in scope, non-excluded, reproducible, and has clear
   impact.

The agent handles workflow tracking, scope reminders, notes, leads, and evidence
bookkeeping.

## Working Loop

Use these phases in order.

### 1. Select

Ask:

```text
Candidate programs are <A>, <B>, <C>. Check policy and eligibility. For each,
define a <=1h kill-test for stored XSS through object/name fields. Do not hunt.
```

After you try the kill-tests:

```text
Here are the kill-test results:
- <A>: <result>
- <B>: <result>
- <C>: <result>

Recommend one target and one focus feature only.
```

### 2. Provision

Ask:

```text
Target is <handle>. Focus feature is <feature>. I can create <object> with a
name/title marker. Guide me until the feature is enabled. Do not hunt yet.
```

Enabled means the feature actually works at the bug shape. A page that loads is
not enough.

### 3. Hunt

Ask:

```text
The feature is enabled. Hunt only this feature and this shape/class.

Use Burp/Caido MCP if available. After each experiment, record what was tried,
what happened, and whether it was clean, a signal, or a candidate.

If you notice other bug classes, record them as leads for later. Do not switch
the active hunt.
```

One feature at a time does not mean one feature forever. It means finish or
abandon the current feature before starting another one.

### 4. Verify

Ask:

```text
We have a candidate. Help me make a replayable PoC. Do not mark it verified
until I reproduce it successfully with positive and negative controls.
```

Positive control: the legitimate user/action works.

Negative control: the unauthorized or unsafe path fails.

### 5. Close Or Abandon

Ask:

```text
Show me what is still open. If nothing meaningful remains, close out honestly.
If the path is dead, abandon with the reason.
```

## Do And Do Not

Do:

- kill-test before getting attached to a target;
- hunt one enabled feature at a time;
- use the product first, then inspect Burp/Caido traffic;
- keep unique markers in test data;
- save side ideas as leads;
- replay before verified;
- abandon cold targets quickly.

Do not:

- start with “hunt this handle, go”;
- test a whole app with one shallow idea;
- switch from XSS to authz/SQLi/SSRF mid-hunt;
- keep testing a disabled or policy-excluded feature;
- rely on chat memory for what is left;
- submit “looks vulnerable” without reproduction.

## Stop Conditions

Stop or switch target/feature when:

- the program excludes the class;
- the asset is not eligible for submission;
- account creation or testing is not allowed;
- the field is not user-controlled;
- the value never renders in another view;
- every reachable render escapes the value;
- you cannot reproduce the candidate twice;
- the agent suggests testing outside authorized scope.

## If You Find Nothing

Do not add more process. Treat the result as data:

- target/tier infertile -> choose a new portfolio;
- feature weak -> choose a different feature or shape;
- too shallow -> do one deeper pass on the enabled feature;
- too much proxy replay -> create new product state first.

Then run another clean cycle.
