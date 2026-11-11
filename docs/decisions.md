# Decision records — November 2026

1. **Model actual constraints.** A potential transaction must satisfy skills, minimum quality, availability and seller
   payout after the platform fee. A job that expires remains in the fulfilment denominator.
2. **Audit money.** Acquisition costs apply to every arriving buyer, not only successful matches. GMV reconciles exactly
   to seller payouts and platform fees; contribution subtracts declared variable costs.
3. **Retain a simple baseline.** The focused oldest-first policy achieves 93.7% mean fill; the focused daily optimizer
   reaches 90.3% across 40 paired seeds. Daily optimization lacks an age/expiry objective, so the simpler policy performs
   better on cohort fulfilment. The preferred pilot candidate was therefore revised to oldest-first.
4. **Consider both sides of monetization.** A higher fee improves modeled contribution but reduces feasible payouts and
   fill. Behavioral elasticity remains unknown and must be measured before making a pricing recommendation.
5. **Separate simulation noise from model uncertainty.** Paired bootstrap intervals address finite seeds only. Unknown
   demand, repeat use, service failure and competition cannot be repaired by running more simulations.

The cohort-level result does not imply that greedy is universally optimal. A future age-aware optimizer is a testable
alternative; it is not claimed to be implemented here.
