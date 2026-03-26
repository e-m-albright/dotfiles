# Expert Panel Reference

Archived from system-prompt-advisor.md. These are practitioners with documented,
falsifiable thinking frameworks. Use as source material when drafting domain-specific
project prompts or when you want to re-add named experts to a system prompt.

## Selection Criteria

Each person is here because they have a specific, demonstrably productive thinking
framework that produces better outcomes than consensus. The test: has this person
been right when popular opinion was wrong, and can you articulate why their
framework produces that result?

## ML / AI Engineering

- **Andrej Karpathy**: Radical clarity, understand every layer. "If you can't implement it from scratch, you don't understand it enough to debug it in production."
- **Rich Sutton**: The Bitter Lesson. General methods leveraging computation beat clever domain-specific engineering. Every time.
- **Francois Chollet**: Abstraction should reduce cognitive load, not add it. Distinguish rigorously between memorization and generalization.
- **Chris Olah**: Look inside the box. Neural networks learn interpretable features. If your model behaves unexpectedly, the answer is in the weights.
- **Jeremy Howard**: Start with the simplest thing using the best pretrained model. You'll be surprised how often that's the final answer.
- **George Hotz**: Most software is 10-100x more complex than necessary. Useful heuristic, but apply critically. Sometimes the complexity is load-bearing.
- **Jim Keller**: Performance comes from understanding the full stack. Most performance problems are architecture problems disguised as implementation problems.
- **Chip Huyen**: Most ML projects fail not because the model is bad, but because the system around it is bad: data quality, serving, monitoring, feedback loops.

## Healthcare & Evidence-Based Medicine

- **John Ioannidis**: Most published findings are false. Ask "how likely is this to replicate?" not "was this published?"
- **Peter Attia**: Healthspan as engineering problem. The four horsemen (CVD, cancer, neurodegeneration, metabolic dysfunction). Train and eat to delay all four.
- **Vinay Prasad**: Surrogate endpoints often don't translate to outcomes that matter. The gap between "FDA approved" and "proven to help patients" is larger than assumed.
- **Atul Gawande**: Medical failures are execution failures in complex systems. Checklists and process design save more lives than brilliant individuals.
- **Eric Topol**: AI's biggest medical opportunity is giving doctors back time, not replacing them. Evaluate AI health claims against actual clinical evidence.
- **Judea Pearl**: You cannot answer causal questions with statistical tools alone. Most ML operates at association (level 1); medicine needs intervention and counterfactuals (levels 2-3).
- **Ben Goldacre**: Pharmaceutical evidence is structurally compromised by selective publication and industry control. Assume distortion until proven otherwise.

## Strength Training & Physical Performance

- **Greg Nuckols**: Progressive overload, sufficient volume, adequate recovery explain 90%+ of results. Everything else is margin optimization.
- **Mike Israetel**: Volume drives hypertrophy up to your Maximum Recoverable Volume. Beyond that, you're accumulating fatigue without stimulus.
- **Mark Rippetoe**: Novice linear progression is the most productive training period. Don't waste it on complexity you don't need yet. (His framework is strongest for novices; diminishing returns for intermediates.)
- **Andy Galpin**: Different adaptations require different stimuli and can interfere. Smart programming sequences competing adaptations.
- **Dan John**: Loaded carry, squat, hinge, push, pull, and consistency. Simple movements you sustain beat complex programs you abandon.
- **Layne Norton**: Energy balance determines weight change. Protein is the most important macro. Almost everything else in nutrition is a minor variable the industry inflates.

## Parenting & Child Development

- **Alison Gopnik**: Children are the R&D department of the human species. Their exploration and experimentation is optimal learning, not misbehavior.
- **Emily Oster**: Most agonized-over parenting decisions have much smaller effect sizes than the discourse implies. A few things matter a lot; most matter little.
- **Becky Kennedy**: Two things can be true: firm boundary AND validated feelings. Most parenting struggles come from thinking these conflict.
- **Ross Greene**: Kids do well when they can. Behavioral problems are skill deficits, not willfulness. Identify the lagging skill, solve collaboratively.
- **Gordon Neufeld**: Attachment-first framework. Relationship security is the foundation everything else builds on. (Less empirically rigorous than Gopnik/Oster/Greene; use for the core attachment principle, not his more contested claims about peer orientation.)

## Cross-Domain Systems Thinking

- **Nassim Taleb**: In fat-tailed domains, prediction is impossible. Build antifragility (benefit from shocks) rather than predicting. Via negativa: improve by removing.
- **Richard Feynman**: "You must not fool yourself, and you are the easiest person to fool." If you can't explain it simply, you don't understand it. Names are not understanding.
- **Claude Shannon**: Every problem has an essential structure separable from surface complexity. If you're struggling, you haven't simplified enough.
- **Herbert Simon**: Satisficing (first option meeting your threshold) often outperforms maximizing in real-world conditions. Know when "good enough" is optimal.

## Candidates Not Included (Consider for Domain-Specific Prompts)

- **Patrick Collison / Michael Nielsen**: Research taste and meta-learning. "How to do great work" thinking.
- **John Tukey**: "An approximate answer to the right question is worth far more than an exact answer to the wrong question."
