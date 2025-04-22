
variable "ibmcloud_api_key" {
  description = "API key for IBM Cloud access"
  type        = string
  default     = "PLACEHOLDER_API_KEY" 
}
variable "region" {
  description = "IBM Cloud region"
  type        = string
  default     = "us-south"
}
variable "resource_group" {
  description = "Resource group name"
  type        = string
  default     = "Default" 
}
variable "vpc_name" {
  type = string

}
variable "enable_logging" {
  description = "Enable logging for services"
  type        = bool
  default     = "true" 
}