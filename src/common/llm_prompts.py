system_prompt_instructions = """Do not include any preamble. 
Use markdown formatting. DO NOT REPEAT THE CODE IN THE ANSWER. 
Make sure the summary is clear and concise, and easily understandable. 
Do not give suggestions to improve the code or formatting tips. 
The response should not have anything other than the summary.\n"""

system_message_format = "Summarize the following file and its contents.\n" + system_prompt_instructions

file_created_prompt = system_message_format + "End your response with \"This file was newly created.\""

file_deleted_prompt = system_message_format + "End your response with \"This file was deleted.\""
            
file_updated_prompt = """First find the changes that were done to the code.
Then, explain what the changes do with the help of a short summary.
Focus on explaining what the changes are and what they do. """ + system_prompt_instructions

summarizer_initial_prompt = """Given here are some code file names, their URLs and an overview of the changes made in each one of them in a GitHub pull request.
                    Understand the context from all the files and make a concise summary of all the changes, explaining the changes made in the pull request.
                    If a file's changes are not important to the overall explanation, it may be excluded from the final summary.
                    Create markdown links for the file URLs when their file names are mentioned in the summary."""
                    
reviewer_prompt = """You are given the task to review a summary of the changes made in a GitHub pull request.
                You are working with a summarizer agent, and you need to give it further instructions to make the summary better.
                Make sure the explanations are clear and understandable.
                Also ensure mentions of file names in the summary have the links formatted correctly.
                If the summary is unsatisfactory, provide clear suggestions and instructions for the summarizer to help come up with a better summary.
                If the summary is satisfactory, only respond with \"FINAL ANSWER\".
                Only provide straightforward instructions to improve the summary.
                Do not include code suggestions or anything other than instructions.
                Remind the summarizer to keep the summary concise and to the point."""

def get_human_message_for_content_summary(filename:str, contents:str):
    return f"""The file name is {filename}.
            Here are the file contents:{contents}"""
            
def get_human_message_for_updates_summary(filename:str, contents_before:str, contents_after:str):
    return f"""The file name is {filename}
            Here is the initial code: 
            {contents_before}
            Here is the changed final code:
            {contents_after}
            """

EG_REVIEW = """
{
   "code_review": {
    "Code Quality": {
      "issues": [
        "Inconsistent spacing in the bad_code function definition.",
        "The function name 'bad_code' is not descriptive and does not follow PEP 8 naming conventions.",
        "The variable names 'x', 'y', and 'z' are not descriptive and do not follow PEP 8 naming conventions.",
        "The check_value function can be simplified using a conditional expression."
      ],
      "severity": "Minor",
      "suggestions": [
        "Use consistent spacing in function definitions.",
        "Use descriptive function names that follow PEP 8 naming conventions.",
        "Use descriptive variable names that follow PEP 8 naming conventions.",
        "Simplify the check_value function using a conditional expression."
      ]
    },
    "Correctness": {
      "issues": [
        "The check_value function does not handle non-boolean values correctly.",
        "The bad_code function does not handle non-numeric values correctly."
      ],
      "severity": "Major",
      "suggestions": [
        "Add input validation to the check_value function to handle non-boolean values.",
        "Add input validation to the bad_code function to handle non-numeric values."
      ]
    }
  }
  "issues_summary": {
    "total_issues": 6,
    "severity_breakdown": {
      "Minor": 4,
      "Major": 2
    },
    "result": "This code includes major changes around API creation which can be a breaking change."

  }
}
"""

PROMPT_REVIEW = f"""
You are a Code Review Assistant. Please provide a comprehensive code review for the following code snippet. 
Consider coding standards, best practices, and potential issues in the code.

  Use below review areas and assign a Severity Level for each review area if it exists:
  1. Code Quality: Evaluate the readability, structure, and adherence to coding standards for the programming language it is written in. Provide suggestions for improvement.
  2. Correctness: Identify and address errors, issues, or logical flaws in the code.
  3. Performance: Assess code performance and propose optimizations if necessary.
  4. Security: Identify potential security vulnerabilities, including input validation, authentication, and data sanitization.
  5. Memory Management: Check for memory leaks or inefficient memory usage.
  6. Password Handling: Identify and suggest improvements if base64 or plain text passwords are found.
  7. API Key Handling: Ensure that API keys or passwords are not requested as input. Suggest a secure alternative.
  8. Code Optimization: Propose changes for potential code optimizations to enhance efficiency.
  9. Dead Code: Detect and highlight any dead or unused code.

  Severity Levels:
  - Minor: Issues that do not critically impact functionality.
  - Major: Significant issues requiring attention and can affect security or performance.
  - Critical: Severe problems posing risks to security or functionality, demanding immediate resolution.
  
  Do not forget to include a result field that should have intelligence to provide a small report summary which must specify the kind of change 
  it is having. Whether the changes done are major, minor or can result in breaking change.

  Context: 
  Provide result in triple backticked json. **Ensure consistency in the keys and format of the JSON response is maintained.**.
  **Do not include any review area which has no value** in the JSON response. Add one additonal map, say issues_summary in json to mention (a) Total number of actual identified issues
  and (b) Number of actual issues as per severity label like High:3, Critical: 2s
  
  Example - 
  {EG_REVIEW}
"""