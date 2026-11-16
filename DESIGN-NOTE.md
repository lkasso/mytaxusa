## Design note

**Audience**

The lab is for engineers who are comfortable in Python and have called an LLM API before. They have probably used the Claude Code CLI and they have made their own skills and CLAUDE.md files. Ideally they have also written their own agent loop and are somewhat familiar with some CLAUDE APIs/SDKs.

They don't know why they would use the Agent SDK over the Messages API. And they don't think about file access, context handling, and permission checks when working with LLMs yet either.

The lab is 201 level. It moves quickly through the agent loop and the basic `ClaudeSDKClient` features, and spends most of its time on the features that change how you'd build a real agent.

**Scope**

Everything is built around a realistic use case which is a pre-filing reviewer for MyTaxUSA, a tax app. To make it feel realistic, the MyTaxUSA site has some real functionality like 2024 IRS tax rules built-in and even W-2 form intake capability, this all produces a realistic Form 1040.

The agent that students build ties a return to its source documents, compares it to last year's return, checks credits, and gives a pass, warn or hold verdict. This makes it so that is has to use a bunch of feature provided by the Agent SDK. The review standards become a `CLAUDE.md`, the credit rules become a skill, per-document checking becomes a subagent, and so on.

I left out MCP, custom tools, model selection, streaming, caching, memory, sessions, and full evals on purpose.

Because of the time constraints and the fact that I wanted to make this feel "real", I pre-built the Flask app, the workspace builder, and two of the skills. This way, the lab time goes to the SDK and not to plumbing.

**With more time**

I'd make the UI less hacky so the entire app feels even more realistic. Then I'd polish everything and cut the lab down hard. It's dense right now, and a tighter version would land better in 60 minutes.

I may consider swapping some features that I put in the stretch goals instead.

**How I used Claude**

I used Claude at every stage.

First, I came in with a few candidate use cases and worked with Claude to narrow them down to the one that best fit the Agent SDK best.

Then, I built the MyTaxUSA site and all the pre-build items with Claude.

Finally, I drafted the lab with Claude. This involved hours of back and forth until I was satisfied.

I also built the presentation with Claude artifacts and reworked it heavily until the 6-hour deadline.

**Overrode / caught issue with Claude**

I didn't take any of the lab or presentation output as-is. My relationship with Claude is to carefully go over everything generated and make sure it's correct. I always participate in my own labs and pretend to be a student over and over again to make sure the class is good.

For example, when Claude helped me create part 1 of my lab, it was all done in one step, expecting students to write the entire loop and options in one go! That is not a good way to write a tutorial so I split it up into smaller, well defined steps (loop first, then some options, then more options...). Then I asked Claude to rewrite the lab accoridngly, using part 1 to build part 2 and so on.

When Claude first drafted my slides, in the guardrails slide, Claude claimed a hook would stop a W-2 that said "pass this return." A hook blocks tool calls, not verdicts, so I caught it and changed the example to a real prompt injection that tries to read other taxpayers' returns. Claude also titled a slide "Four options shape what the reviewer does," which suggested the SDK only has four options. I rewrote it to make clear these are a few of many.
