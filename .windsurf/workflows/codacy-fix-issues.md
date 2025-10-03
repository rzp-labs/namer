---
description: Find and fix issues in your project using Codacy local analysis
auto_execution_mode: 3
---

If the user didn't provide any files as context, ask which files they want to analyse.

Once you have the files to analyse:

1. Run the 'codacy_cli_analyze' tool for each of the files, with the following params:
   - rootPath: set to the workspace path
   - file: set to the path of the file
   - tool: leave empty or unset
2. If any issues are found in the files, propose and apply fixes for them.
3. If you encounter that Codacy is applying a tool to the project that it shouldn't, don't try to find the configuration of Codacy, just let the user know it's a false positive issue.
