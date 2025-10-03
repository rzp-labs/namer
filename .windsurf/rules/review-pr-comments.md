---
trigger: manual
description: Process PR review comments, create prioritized Linear issues, and resolve urgent blocking issues with immediate code fixes.
---

---
Rule: Post-PR Review Issue Management and Resolution

## Trigger Condition
Execute this rule when a PR review status changes to "Changes Requested" or when manually triggered after receiving review feedback.
---

## Detailed Workflow

### Phase 1: Comment Collection and Analysis

1. **Retrieve PR Comments**
   ```
   Action: Use GitKraken `pull_request_get_comments` 
   Parameters: 
   - PR ID: [current_pr_id]
   - Include: resolved and unresolved comments
   - Filter: comments from current review cycle only
   ```

2. **Parse and Categorize Comments**
   - Extract comment metadata:
     - Author (reviewer name/handle)
     - Line number/file path
     - Comment thread ID
     - Timestamp
     - Resolution status
   - Identify comment types:
     - Code change requests
     - Questions requiring clarification
     - Suggestions for improvement
     - Documentation requests
     - Style/formatting issues

### Phase 2: Priority Classification

For each comment, determine priority using these criteria:

**URGENT (Priority 1) - Blocking Issues:**
- Comments containing keywords: "blocker", "blocking", "critical", "must fix", "security", "vulnerability", "breaking change"
- Syntax errors or code that won't compile
- Security vulnerabilities explicitly mentioned
- Data loss risks
- Production-breaking changes
- Failing tests directly caused by PR changes

**HIGH (Priority 2) - Next PR Resolution:**
- Comments marked as "required" or "needs fixing"
- Logic errors that don't break compilation
- Missing error handling
- Performance issues with clear impact
- Incomplete feature implementation
- Missing critical documentation for public APIs

**MEDIUM (Priority 3) - Post-Feature Completion:**
- Code optimization suggestions
- Refactoring recommendations
- Non-critical test additions
- Documentation improvements for internal code
- Code style improvements beyond team standards
- Minor UX enhancements

**LOW (Priority 4) - Future Consideration:**
- "Nice to have" suggestions
- Future enhancement ideas
- Optional refactoring
- Comments starting with "Consider..." or "Maybe..."
- Style preferences not in coding standards
- Performance micro-optimizations

### Phase 3: Linear Issue Creation

For each categorized comment:

1. **Create Linear Issue**
   ```
   Action: Use Linear `create_issue`
   Parameters:
   - Title: "[PR-{pr_number}] {comment_summary}"
   - Description: 
     ```
     **Original PR:** {pr_link}
     **Reviewer:** {reviewer_name}
     **File:** {file_path}
     **Line(s):** {line_numbers}
     
     **Review Comment:**
     {full_comment_text}
     
     **Context:**
     {code_snippet_around_comment}
     
     **Acceptance Criteria:**
     - [ ] Address reviewer's concern
     - [ ] Update code/documentation as needed
     - [ ] Respond to reviewer in PR
     - [ ] Verify changes don't break existing functionality
     ```
   - Priority: {calculated_priority_1_to_4}
   - Labels: ["pr-feedback", "review-{pr_number}", "{priority_label}"]
   - Assignee: Current PR author
   - Due Date: 
     - Urgent: Today
     - High: Within 2 days
     - Medium: Within 1 week
     - Low: No due date
   ```

2. **Link Issues to PR**
   - Add Linear issue URL as a comment reply in GitKraken
   - Format: "📋 Tracked in Linear: {issue_link}"

### Phase 4: Urgent Issue Resolution

For all URGENT priority issues:

1. **Analyze Required Changes**
   - Identify affected files
   - Determine change scope
   - Check for interdependencies

2. **Implement Fixes**
   ```
   For each urgent issue:
   a. Navigate to affected file(s)
   b. Apply necessary code changes:
      - Fix compilation errors
      - Resolve security vulnerabilities
      - Correct breaking changes
      - Fix failing tests
   c. Run local validation:
      - Compile/build project
      - Run affected unit tests
      - Run linter/formatter
   d. Document change in issue:
      - Update Linear issue with resolution notes
      - Mark subtasks as complete
   ```

3. **Commit and Push Changes**
   ```
   Action: Git operations
   Steps:
   1. Stage all modified files
   2. Create commit with message:
      "fix: Address urgent PR review comments
      
      Resolved blocking issues:
      - {issue_1_summary} (Linear: {issue_id})
      - {issue_2_summary} (Linear: {issue_id})
      ...
      
      Refs: PR #{pr_number}"
   3. Push to remote branch: git push origin {current_branch}
   4. Add comment to PR: "✅ All urgent/blocking issues have been resolved and pushed in commit {commit_sha}"
   ```

### Phase 5: Status Update and Reporting

1. **Update PR Thread**
   - Post summary comment:
   ```
   ## Review Feedback Processing Complete
   
   ### Issues Created:
   - 🔴 Urgent: {count} issues (resolved ✓)
   - 🟠 High: {count} issues
   - 🟡 Medium: {count} issues
   - 🟢 Low: {count} issues
   
   ### Linear Project: {linear_project_link}
   ### Next Steps: High priority issues will be addressed in the next commit cycle
   ```

2. **Update Linear**
   - Move urgent issues to "Done" status
   - Add PR link to all created issues

## Error Handling

- **API Failures**: Retry 3 times with exponential backoff
- **Merge Conflicts**: Alert user and pause execution
- **Test Failures**: Document in Linear issue and alert user
- **Permission Errors**: Log and notify about access issues

## Configuration Variables

```yaml
config:
  gitkraken:
    pr_id: "${current_pr_id}"
    repo: "${repository_name}"
  linear:
    team_id: "${linear_team_id}"
    project_id: "${linear_project_id}"
  priorities:
    urgent_keywords: ["blocker", "blocking", "critical", "security", "vulnerability"]
    high_keywords: ["required", "must", "needs fixing", "error"]
    medium_keywords: ["should", "recommend", "improve"]
    low_keywords: ["consider", "maybe", "nice to have", "future"]
  auto_resolve:
    enabled: true
    only_urgent: true
    require_tests_pass: true
```

## Execution Conditions

- Only run on PRs with "Changes Requested" status
- Require write access to both GitKraken and Linear
- Ensure no ongoing rebase or merge operations
- Verify CI/CD pipeline is not currently running

## Rollback Strategy

If urgent fixes cause new issues:
1. Revert the commit: `git revert {commit_sha}`
2. Update Linear issues with failure notes
3. Alert PR author and reviewers
4. Create new "URGENT" issue for the regression

This rule ensures systematic handling of PR feedback, maintaining traceability through Linear, and immediate resolution of blocking issues to keep development velocity high.