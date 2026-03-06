# AdverseIQ — Expected Outputs Per Mode
**Test case: Tramadol 50mg QID + Sertraline 100mg OD | Fever, confusion, muscle rigidity**
**recentlyAdded: tramadol**

---

## Rapid Check

**What it does:** Single-call confirmation. K2 looks at the drug pair and the symptom and answers one question: is the known interaction consistent with what the patient is experiencing?

**Expected response time:** 10–20 seconds

---

### What you should see in the UI

**Urgency banner**
```
🔴 EMERGENT
Tramadol and sertraline both have serotonergic properties. Combined use with fever,
confusion and muscle rigidity is consistent with serotonin syndrome, which requires
immediate clinical evaluation.
```

**Interaction confirmed**
```
Interaction found: Yes
Mechanism: Tramadol inhibits serotonin reuptake (SNRI activity) and sertraline is
an SSRI — combined serotonergic load exceeds the threshold for serotonin syndrome.
```

**Confidence**
```
78%
▲ K2 confidence estimate: drug pair is well-documented in literature
```

**Recommendation**
```
Discontinue tramadol immediately. Assess Hunter Criteria for serotonin syndrome.
If confirmed, consider cyproheptadine. Monitor vitals continuously.
```

**Safer Alternative Considered**
```
Replace tramadol with acetaminophen (paracetamol) for mild-to-moderate pain,
or a short-course NSAID if no GI or renal contraindication. Avoid all opioids
with serotonergic properties in any patient on an SSRI or SNRI.
```

---

### What you should NOT see in Rapid Check
- No hypothesis list
- No causal step chain
- No tree visualisation
- No PubMed references
- No tools_used list (Rapid Check uses the standard endpoint, no tool calling)

---

## Mechanism Trace

**What it does:** Constructs a full pharmacological causal chain from drug action through to the observed symptom. Each step is grounded with a mechanism and evidence citation. K2 receives the full list of database interactions and reasons through them.

**Expected response time:** 20–40 seconds

---

### What you should see in the UI

**Urgency banner**
```
🔴 EMERGENT
Multiple serotonergic agents with classic triad of fever, altered mental status
and neuromuscular abnormality. Consistent with serotonin syndrome.
```

**Causal chain — 4–5 steps, each rendered as a card**

```
Step 1
Mechanism:        Sertraline blocks the serotonin reuptake transporter (SERT),
                  increasing synaptic serotonin at 5-HT1A and 5-HT2A receptors.
Expected finding: Elevated serotonergic tone at baseline.
Evidence:         Sertraline SSRI mechanism — established pharmacology.
Source:           mechanism
```

```
Step 2
Mechanism:        Tramadol independently inhibits serotonin and noradrenaline
                  reuptake (SNRI activity) in addition to its weak mu-opioid agonism.
Expected finding: Second independent source of serotonergic excess.
Evidence:         Tramadol dual mechanism — Boyer & Shannon, NEJM 2005.
Source:           literature
```

```
Step 3
Mechanism:        Combined SERT blockade from both agents overwhelms autoreceptor
                  feedback, producing sustained 5-HT2A receptor hyperstimulation.
Expected finding: Serotonin syndrome triad — hyperthermia, altered consciousness,
                  neuromuscular excitability.
Evidence:         Sternbach criteria and Hunter criteria for serotonin syndrome.
Source:           database
```

```
Step 4
Mechanism:        CYP2D6 is the primary metabolic pathway for both tramadol and
                  sertraline. Sertraline inhibits CYP2D6, reducing tramadol clearance
                  and increasing its plasma concentration.
Expected finding: Amplified tramadol exposure — pharmacokinetic potentiation of
                  the pharmacodynamic interaction.
Evidence:         CYP2D6 inhibition by sertraline — established drug interaction.
Source:           database
```

**Confidence**
```
91%
▲ Known interaction found in database
▲ Mechanism is pharmacologically plausible
▲ Reported symptom matches expected pharmacological effect
```

**Confidence factors from K2** (K2's own reasoning, shown above engine annotations)
```
▲ Two independent serotonergic mechanisms converge — high weight
▲ CYP2D6 kinetic amplification adds pharmacokinetic component — medium weight
▲ Classic symptom triad present — high weight
```

**Safer Alternative Considered**
```
Replace tramadol with acetaminophen for mild-to-moderate pain. If opioid analgesia
is required, morphine has no meaningful serotonergic activity and is not a CYP2D6
substrate — discuss with prescriber.
```

---

### What you should NOT see in Mechanism Trace
- No hypothesis list or hypothesis cards
- No tree visualisation
- No tools_used Investigation tab (standard endpoint, no tool calling)

---

## Mystery Solver — Non-Streaming

**What it does:** Full agentic investigation. K2 receives the patient case and autonomously calls tools to gather evidence before forming hypotheses. This path applies logprob calibration to the confidence score — the most accurate result.

**Expected response time:** 60–120 seconds (no live feedback — spinner only)

**Use this path for:** PDF export, saving to database, the fully calibrated result.

---

### What you should see when the result arrives

**Urgency banner**
```
🔴 EMERGENT
Serotonin syndrome is a life-threatening emergency. The combination of tramadol
(serotonergic opioid) and sertraline (SSRI) with fever, confusion and rigidity
meets Hunter Criteria. Immediate discontinuation and clinical management required.
```

**Hypothesis cards — typically 3–5 hypotheses**

```
H1 — Serotonin Syndrome                                        [SUPPORTED]  94%
Mechanism: Dual serotonergic mechanism — SERT blockade by both agents,
           compounded by CYP2D6 inhibition increasing tramadol exposure.
Supporting: Known drug-drug interaction in database; symptom triad matches
            Hunter Criteria; tramadol recently added (temporal correlation);
            PubMed: 3 case reports confirm this presentation (PMIDs: 12345678,
            23456789, 34567890)
Rejecting:  None
```

```
H2 — Anticholinergic Toxidrome                                 [REJECTED]   8%
Mechanism: Anticholinergic receptor blockade causing CNS and autonomic effects.
Supporting: Confusion is consistent.
Rejecting:  Neither tramadol nor sertraline has significant anticholinergic
            activity. Muscle rigidity and fever are not typical. No anticholinergic
            agent present in the medication list.
```

```
H3 — Disease Progression / Non-drug Cause                      [POSSIBLE]  15%
Mechanism: CNS infection, neuroleptic malignant syndrome, or other febrile illness.
Supporting: Fever and confusion can have non-drug causes.
Rejecting:  Temporal correlation with tramadol initiation is strong. No
            antipsychotic or dopamine antagonist present to explain NMS.
            Drug interaction is more parsimonious.
```

**Overall confidence**
```
91%
▲ Known interaction found in database
▲ PubMed literature supports this interaction
▲ Model certainty check: model certainty high (0.87) — score kept
```

**Investigation tab (tools_used)**
```
✓ Checked interaction database        (lookup_drug_interaction × 2 pairs)
✓ Identified drug class               (get_drug_class — tramadol, sertraline)
✓ Checked CYP enzyme profile          (get_cyp_profile — tramadol, sertraline)
✓ Searched PubMed literature          (search_pubmed — serotonin syndrome case reports)
✓ Generated safer alternative         (get_safe_alternative)
```

**Safer Alternative Considered**
```
Replace tramadol with acetaminophen (paracetamol) for mild-to-moderate pain,
or a short-course low-dose NSAID if no GI or renal contraindication. Avoid all
opioids with serotonergic properties (fentanyl, meperidine, methadone) in any
patient on an SSRI or SNRI.
```

**Reasoning tree**
React Flow canvas with hypothesis nodes, evidence nodes, and directional edges connecting evidence to hypotheses. H1 node is highlighted. Rejected hypotheses are greyed out.

---

## Mystery Solver — Live Streaming

**What it does:** Same agentic investigation as non-streaming, but you watch K2 think and call tools in real time. No logprob calibration on this path — the confidence score is K2's raw value adjusted by the confidence engine annotations only.

**Expected response time:** First thinking tokens in 2–5 seconds. Result arrives 60–120 seconds after submission.

**Use this path for:** The live demo, the primary user experience.

---

### What you should see happen, in order

**Stage label updates — top of the results panel**
```
1. "Normalizing drug names"
2. "Focusing on recently changed drug: tramadol"
3. "Building reasoning tree"        ← appears after result arrives
```

**Thinking stream — scrolling monospace text block**

This starts filling within a few seconds. It will look roughly like:

```
Let me investigate this case systematically. The patient is on sertraline, an SSRI,
and tramadol was recently added. I need to check all drug pair interactions first.

Looking up tramadol + sertraline interaction in the database...

The database confirms a major interaction — dual serotonergic mechanism. Tramadol
has SNRI activity in addition to opioid agonism. Combined with sertraline's SERT
blockade this creates significant risk of serotonin syndrome.

Let me check the drug classes to assess the full serotonergic load...

Tramadol is classified as opioid_agonist, snri, serotonergic, analgesic. This
confirms the mechanism. Sertraline is ssri, serotonergic, antidepressant.

I should also verify the CYP2D6 interaction — sertraline inhibits CYP2D6 and
tramadol is a CYP2D6 substrate, so sertraline would reduce tramadol clearance
and increase its plasma concentration, amplifying the pharmacodynamic risk.

Searching PubMed for case reports...

Found 3 recent case reports confirming serotonin syndrome with this combination.
PMIDs 12345678, 23456789 describe classic presentations matching this patient.

Now I'll identify a safer alternative to tramadol...

Given the patient needs analgesia and must remain on sertraline, acetaminophen
is the safest substitute with no serotonergic activity.

I have sufficient evidence to formulate my hypotheses.
```

**Tool summary — appears after thinking stream ends, before result**
```
K2 autonomously called 5 tools: lookup_drug_interaction, get_drug_class,
get_cyp_profile, search_pubmed, get_safe_alternative
```

**Result — same content as non-streaming**, rendered as the full results dashboard:
- Urgency banner
- Hypothesis cards
- Confidence bar with annotations
- Investigation tab
- Safer Alternative section
- Reasoning tree

---

## Quick Comparison

| | Rapid Check | Mechanism Trace | Mystery Solver |
|---|---|---|---|
| Response time | 10–20s | 20–40s | 60–120s |
| K2 calls | 1 + 1 (safe alt) | 1 + 1 (safe alt) | Agent loop (4–8 turns) |
| Endpoint | Standard | Standard | Agentic (build-api) |
| JSON mode | No (repair pipeline) | No (repair pipeline) | Yes (guaranteed) |
| Logprob calibration | No | No | Yes (non-streaming only) |
| Tool calls visible | No | No | Yes — Investigation tab |
| Thinking stream | No | No | Yes (streaming path) |
| Urgency source | K2 + escalation guard | K2 + escalation guard | K2 + escalation guard |
| Safe alternative | Yes | Yes | Yes (K2-initiated tool) |
| Hypothesis list | No | No | Yes |
| Causal chain | Single step | 4–5 steps | Inside each hypothesis |
| Tree visualisation | No | No | Yes |
| PubMed refs | No | No | Yes (PMIDs per hypothesis) |
| Best used for | Quick triage | Explaining mechanism | Full diagnostic workup |

---

## Red Flags — Something Is Wrong

| What you see | What it means |
|---|---|
| Urgency is `routine` for the serotonin case | K2 failed and demo fallback returned — check backend logs |
| Confidence is exactly 50 | K2 returned no confidence value — JSON parse likely failed |
| `tools_used` is empty on Mystery Solver | Agent loop returned fallback — K2 call timed out or failed |
| Thinking stream never starts | SSE connection not reaching Render — check `NEXT_PUBLIC_API_URL` |
| Thinking stream starts but result never arrives | K2 timed out at 120s — retry once; if persistent, use `GET /api/cases/serotonin` |
| Safe alternative is absent | K2 safe alternative call failed silently — static fallback also failed |
| No tool summary appears | K2 completed in one turn without tool calls — prompt injection may have failed |

---

*AdverseIQ — Expected Outputs Reference — March 2026*