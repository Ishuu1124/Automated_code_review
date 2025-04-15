# AI- Automated Terraform Code Review ([Epic-13090](https://github.ibm.com/GoldenEye/issues/issues/13090))

|Discussion 1| 8th-April-25 | Recording Link |
|---|---|---|

## Minutes
* Focus has to be on **Naming** and **Ordering** of `variables.tf` and `outputs.tf`
* This is TIM specific application we are working on and should focus on internals of TIM repos. (No plans to distibute to other teams)
* Do not consider Variable description for now.
* There were some sugestions around grouping but what is of importance is that the **Required** inputs has to be at top of the file.
* While providing suggestion for variable names, we need to arrive at some naming convention, for example, resource_tags for VPC can be like - vpc_resource_tags etc. But this has to be consistent.
* Use Granite models only - Explore which of the Granite models is good for our case, coding one or whatever is latest based on trial/test.
* Deployment approach - Github application hosted on Code Engine (have to create a separate bot)
* Very important : Keep the scope smaller, get the POC functional first.
* Any discussions/progress should be taken to next deep dive or in scrum calls with Ireland team.
________
