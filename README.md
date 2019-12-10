# Terraform Wrapper

For help the usage of Terraform command and workflow for provision infrastructure on Azure, I created this Wrapper Terraform that englobe all Terraform lifecycle operations.
This wrapper can also create variables in Azure Pipelines based on terraform outputs.

## Requirements

- Download the terraform cli [download page](https://www.terraform.io/downloads.html)
- This wrapper is developper in Python, so for use it you need to install Python on your machine https://www.python.org/downloads/ + pip
- Install python dependecies packages (referenced in requirements.txt) by run the commande ```pip install -r requirements.txt```
- Use Service principal with secret in Azure

## The configuration file

This Terraform wrapper use Yaml or Json file configuration (like terraform-ic.json/yaml) that contain all parameters for the Terraform execution.
You have samples of json configuration "terraform-dev.json" and Yaml configuration "terraform-dev.yaml" in tf-sample folder

The syntax of the Json configuration is:

```json
{
    "terraform_path": "d:/terraformfiles/",
    "use_azcli":true,
    "backendfile": "dev/backend.tfvars",
    "reconfigure": true,
    "auto-approve": true,
    "run_apply": true,
    "run_output": true,
    "planout": "out.tfplan",
    "azure_credentials":{
        "subscriptionId":"44bc8ffe-XXXXXXXXXX",
        "clientId":"3a93648a-XXXXXXXXXXXXXXXX",
        "tenantId":"c625fb12-XXXXXXXXXXXXXXXXXXXXXXXXXXX",
        "accessKey":"XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
    },
    "varfiles": [
        "IC/env-vars.tfvars"
    ],
    "vars": [
        {
            "name": "createdby",
            "value": "__createdby__"
        },
        {
            "name": "branch",
            "value": "__branch__"
        },
        {
            "name": "release",
            "value": "__release__"
        }
    ],
    "outputToAzDo": {
        "webapp_name": "webappname",
        "instrumentation_key": "ApplicationInsights.InstrumentationKey"
    }
}
```

The yaml configuration is:

```yaml
---
terraform_path: 'tf-sample'
use_azcli: false
backendfile: dev/backend.tfvars
auto-approve: true
reconfigure: true
run_apply: true
run_output: true
planout: out.tfplan
azure_credentials:
  subscriptionId: xxxxx-xxxx-xxxx-xxxxxxx
  clientId: xxxxx-xxxx-xxxx-xxxxxxx
  tenantId: xxxxx-xxxx-xxxx-xxxxxxx
varfiles:
- dev/env-vars.tfvars
vars:
- name: createdby
  value: __createdby__
outputToAzDo:
  webapp_name: webappname
  instrumentation_key: ApplicationInsights.InstrumentationKey
```

|Key|description  |  |
|--|--|--|
| terraform_path | (Optionnal) indicate the path of Terraform templates to execute, if this property is ommited, the wrapper run terraform as the current folder of the wrapper | |
| use_azcli | use the az cli in Terraform code (in case of Terraform need to execute az cli commands)|  |
| backendfile | The path of the backend file that contain the remote backend details [documentation](https://www.terraform.io/docs/backends/types/remote.html#example-configuration-using-cli-input)|  |
| reconfigure | add the -reconfigure option to Init [documentation](terraform.io/docs/commands/init.html#backend-initialization) |  true/false|
| auto-approve | add the --auto-approve option to Apply | true/false  |
| run_apply | Execute the Apply command just after the Plan | true/false |
| planout | The name of the Plan out file |  |
| azure_credentials | keys of Azure SP credentials | subscriptionId, clientId, tenantId, accessKey  |
| varfiles | Array of env-vars files to add in options -var-file |  |
| vars | List to vars to ovverides the var-file  | name: name of the variable ; value: value of the variable |
| outputToAzDo | List of Terraform output to transform to Azure Pipelines variables | key: the terraform output name , value:the Azdo variables to generate |

## The terraform wrapper execution

The wrapper is Python script terraformexec.py, and for use it, we need to pass it some parameters.
This wrapper (terraformexec.py, azdo.py, terraform-dev.yaml) can be placed at the folder of your choice or in the same folder of  your terraform code.
This wrapper Terraform run these operations in order:

At starting the wrapper set the environment variables for Azure authentication , the run the Terraform workflow with:

- The Terraform init
- The terraform format
- The terraform validate
- The terraform plan
- Check if some resources is destroyed
==> if Yes, the wrapper stop the execution --> pass the --acceptdestroy option to allow destroy 
- The terraform apply
- (Optional) Display the output terraform and transform it to Azure DevOps variables

At the end the Wrapper clean the folder.

## terraformexec.py command lines options ##

For get the list of all options execute the command ```python terraformexec.py --help```


|Option|Description  |
|--|--|
|--help  | Display the help  |
|--subscriptionId  | (Optionnal) The subscription Id of the resources provisioned ==> for overide the configuration in json/yaml file configuration|
|--clientId  | (Optionnal) The client Id of SP ==> for overide the configuration in json/yaml file configuration |
|--clientSecret  |  (Required) The client Secret of SP |
|--tenantId  | (Optionnal) The tenant Id of SP ==> for overide the configuration in json/yaml file configuration|
|--accessKey  | (Optionnal) The access key for the storage account of the backend ==> for overide the configuration in json/yaml file configuration|
|--configfile  | (Required) The path of the Json/yaml file configuration of the Terraform execution |
|--terraformpath | (Optionnal) The path of the terraform configuration to execute ==> for override the terraformpath of the configuration json/yaml
|--apply  | (Optionnal) Run the terraform apply juste after the plan ==> for overide the configuration in json/yaml file configuration|
|--acceptdestroy| For allow terraform to destroy resources during the execution |
|--destroy| Run the terraform destroy command instead the apply|
|--verbose or -v| Display logs with all the wrapper parameters|

## Samples of the execution

- sample for execute Terraform locally without Apply (init/plan/output)

```python terraformexec.py --clientSecret "XXXXXXXXXXXXXX" --accessKey "xxxxxxxxxx" --configfile="terraform-dev.yaml" --terraformpath="tf-sample"```


- sample for execute Terraform with apply (init/plan/apply/output)

```python terraformexec.py --clientSecret "XXXXXXXXXXXXXX" --accessKey "xxxxxxxxxx"--configfile="terraform-dev.json" --apply```

- sample for destroy all resources provisioooned in Terraform code

```python terraformexec.py --clientSecret "XXXXXXXXXXXXXX" --accessKey "xxxxxxxxxx" --configfile="terraform-dev.json" --destroy```

- sample for accept the destroy of resources during a terraform execution

```python terraformexec.py --clientSecret "XXXXXXXXXXXXXX" --accessKey "xxxxxxxxxx" --configfile="terraform-dev.json" --acceptdestroy```

## Integration in Azure Pipelines ##

This wrapper can be integrated in Azure Pipelines.
He can create variable based on terraform outputs.

You can remove this integration by remove in the terraformexec.py

- the import
import azdo

- the call of the method
azdo.tfoutputtoAzdo(outputAzdo, jsonObject)
