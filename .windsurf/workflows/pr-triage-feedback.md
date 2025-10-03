---
description: 
auto_execution_mode: 1
---

name: pr-triage feedback
description: Trigger the `review-pr-comments` rule after PR review is complete
version: 1.0.0

triggers:
  - manual: /workflow pr-triage-feedback
  - webhook: pull_request.review_submitted
  - status: pr.status == "changes_requested"

parameters:
  pr_number:
    type: string
    required: false
    default: "${current_pr_number}"
    description: "PR number to process (defaults to current PR)"

workflow:
  steps:
    - id: execute_rule
      name: "Execute AutoReviewToLinearIssues Rule"
      run: |
        echo "🚀 Triggering PR Review Processing for PR #${pr_number}"
        
        @rules.execute AutoReviewToLinearIssues \
          --pr-id ${pr_number} \
          --auto-resolve true
        
        echo "✅ Rule execution triggered"