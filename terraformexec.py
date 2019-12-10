
import os
import argparse
import json
import yaml  # require pip install pyyaml
import sys
import logging
import subprocess
import shutil
import subprocess
import shlex
import azdo


class Terraform(object):
    def __init__(self, az_subscription_id, az_client_id, az_client_secret, az_tenant_id, az_access_key, terraform_path,
                 backendFile, varFiles, logger,  use_apply=True, run_output=True, applyAutoApprove=True,  variables=None,
                 planout="out.tfplan", outputazdo=None, terraformversion="0.12.8", verbose=False, useazcli=False):
        self.backendFile = backendFile
        self.varFiles = varFiles
        self.variables = dict() if variables is None else variables
        self.use_apply = use_apply
        self.applyAutoApprove = applyAutoApprove
        self.planout = planout
        self.outputazdo = outputazdo
        self.run_output = run_output
        self.terraform_version = terraformversion
        self.verbose = verbose
        self.logger = logger
        self.useazcli = useazcli
        self.terraform_path = terraform_path

        if self.useazcli == True:
            os.system("az login --service-principal -u "+az_client_id +
                      " -p " + az_client_secret+" --tenant "+az_tenant_id+"")
            os.system("az account set --subscription "+az_subscription_id+"")

        os.environ["ARM_SUBSCRIPTION_ID"] = az_subscription_id
        os.environ["ARM_CLIENT_ID"] = az_client_id
        os.environ["ARM_CLIENT_SECRET"] = az_client_secret
        os.environ["ARM_TENANT_ID"] = az_tenant_id
        os.environ["ARM_ACCESS_KEY"] = az_access_key

    def Init(self):
        self.logger.info("=> Run Terrform init")
        self.logger.info("[terraform init -no-color -backend-config={} -reconfigure]".format(self.backendFile))
        self.RunCommand("terraform init -no-color -backend-config={} -reconfigure".format(self.backendFile))

    def Format(self):
        self.logger.info("=> Run Terraform fmt")
        self.logger.info("[terraform fmt -no-color]")
        self.RunCommand("terraform fmt -no-color")


    def Validate(self):
        self.logger.info("=> Run Terraform validate")
        self.logger.info("[terraform validate -no-color]")
        return self.RunCommand("terraform validate -no-color")
        

    def Plan(self):
        self.logger.info("=> Run Terrform plan")
        cmd = ""

        for file in self.varFiles:
            cmd += " -var-file="+file
        for var in self.variables:
            cmd += """ -var "{}={}" """.format(var["name"], var["value"])

        cmd += " -out "+self.planout

        self.logger.info(
            "[terraform plan -detailed-exitcode -no-color {}]".format(cmd))
        return self.RunCommand("terraform plan -detailed-exitcode -no-color {}".format(cmd))

    def Apply(self):
        self.logger.info("=> Run Terraform Apply")
        cmd = ""

        if self.applyAutoApprove:
            cmd += "-auto-approve"
            cmd += " "+self.planout
        else:
            for file in self.varFiles:
                cmd += " -var-file="+file
            for var in self.variables:
                cmd += """ -var "{}={}" """.format(var["name"], var["value"])

        self.logger.info("[terraform apply -no-color "+cmd+"]")
        return self.RunCommand("terraform apply -no-color {}".format(cmd))

    def Destroy(self):
        self.logger.info("=> Run Terrform destroy")
        cmd = ""

        for file in self.varFiles:
            cmd += " -var-file="+file
        for var in self.variables:
            cmd += """ -var "{}={}" """.format(var["name"], var["value"])

        cmd += " -auto-approve"

        self.logger.info("[terraform destroy -no-color "+cmd+" "+self.terraform_path+"]")
        self.RunCommand("terraform destroy -no-color {}".format(cmd))

    def Output(self):
        self.logger.info("=> Run terraform output in "+os.getcwd())
        self.logger.info("[terraform output -json]")
        outputjson = os.popen("terraform output -json").read()
        self.logger.info(outputjson)

        # change the JSON string into a JSON object
        jsonObject = json.loads(outputjson)

        with open('outputtf.json', 'w') as outfile:
            self.logger.info("[INFO : Write outputtf.json]")
            json.dump(jsonObject, outfile, indent=4)

        return jsonObject

    def CheckIfDestroy(self):
        self.logger.info("=> Check if Terraform Destroy")
        plan = os.popen("terraform show -json "+self.planout +
                        " | jq .resource_changes[].change.actions[]").read()

        finddelete = plan.find("delete")
        if finddelete > 0:
            self.logger.info("DESTROY : Terraform can't be done")
            return True
        else:
            self.logger.info("Great there is no destroy")
            return False

    def Clean(self):
        if os.path.exists(self.planout):
            self.logger.info("Delete the "+self.planout+" file")
            os.remove(self.planout)
        if os.path.exists(".terraform"):
            self.logger.info("Delete the .terraform folder")
            shutil.rmtree(".terraform")

    def RunCommand(self, command):
        p = subprocess.Popen(command, shell=True,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for line in iter(p.stdout.readline, b''):
            self.logger.info(line.decode("utf-8").replace("\n",""))
        p.stdout.close()
        p.wait()
        return p.returncode


if __name__ == "__main__":

    logger = logging.getLogger()
    handler = logging.StreamHandler()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.info("====> Start Terraform execution")

    parser = argparse.ArgumentParser()

    # authentification Azure pour Terraform avec Service Principal, pour overrider le fichier json de config
    parser.add_argument("--subscriptionId", required=False,
                        help="Azure SubscriptionId Id")
    parser.add_argument("--clientId", required=False, help="Azure Client Id")
    parser.add_argument("--clientSecret", required=True,
                        help="Azure Client Secret")
    parser.add_argument("--tenantId", required=False, help="Azure Tenant Id")
    parser.add_argument("--accessKey", required=False,
                        help="Azure Access Key for storage backend")

    # fichier json de config
    parser.add_argument("--configfile", required=True,
                        help="Configuration file json")

    # fichier json de config
    parser.add_argument("--terraformpath", required=False,
                        help="Terraform files path")

    # permet a Terraform d'appliquer les changements
    parser.add_argument("--apply", help="Run Terraform apply",
                        action="store_true")

    # permet a Terraform de detruire les resources
    parser.add_argument("--acceptdestroy", help="Accept Terraform Destroy operation",
                        action="store_true")

    # Terraform execute destroy au lieu de apply
    parser.add_argument("--destroy", help="Execute Terraform Destroy",
                        action="store_true")

    # verbose mode
    parser.add_argument("-v", "--verbose", help="increase output verbosity",
                        action="store_true")

    args = parser.parse_args()

    # Loading of the configuration file Json / Yaml
    with open(args.configfile) as config:
        name, ext = os.path.splitext(args.configfile)
        #print(name)
        #print(ext)
        if(ext == ".json"):
            data = json.load(config)
        else:
            data = yaml.load(config, Loader=yaml.Loader)

    useazcli = data["use_azcli"]
    backendfile = data["backendfile"]
    autoapprove = data["auto-approve"]
    varfiles = data["varfiles"]  # array of files
    if "vars" in data:
        variables = data["vars"]  # dict of variable name : value
    else:
        variables = None
    outplan = data["planout"]
    outputAzdo = data["outputToAzDo"]
    terraformoutput = data["run_output"]

    terraformpath = os.getcwd()
    if("terraform_path" in data):
        terraformpath = data["terraform_path"]
    if(args.terraformpath != None):
        terraformpath = args.terraformpath

    applyterraform = data["run_apply"]
    if(args.apply == False):
        applyterraform = "false"

    if "subscriptionId" in data["azure_credentials"]:
        azSubscriptionId = data["azure_credentials"]["subscriptionId"]
    if(args.subscriptionId != None):
        azSubscriptionId = args.subscriptionId

    if "clientId" in data["azure_credentials"]:
        azClientId = data["azure_credentials"]["clientId"]
    if(args.clientId != None):
        azClientId = args.clientId

    if "tenantId" in data["azure_credentials"]:
        azTenantId = data["azure_credentials"]["tenantId"]
    if(args.tenantId != None):
        azTenantId = args.tenantId

    if "accessKey" in data["azure_credentials"]:
        azAccessKey = data["azure_credentials"]["accessKey"]
    if(args.accessKey != None):
        azAccessKey = args.accessKey

    acceptDestroy = args.acceptdestroy

    # Affichage des arguments et de la config si -v
    if args.verbose:
        logger.info("========== DEBUG MODE =========================")
        logger.info("useazcli: "+str(useazcli))
        logger.info("backendfile: "+str(backendfile))
        logger.info("autoapprove: "+str(autoapprove))
        logger.info("varfiles: "+str(varfiles))
        logger.info("variables: "+str(variables))
        logger.info("outplan: "+str(outplan))
        logger.info("outputAzdo: "+str(outputAzdo))
        logger.info("terraformpath: "+str(terraformpath))
        logger.info("terraformoutput: "+str(terraformoutput))
        logger.info("applyterraform: "+str(applyterraform))
        logger.info("acceptDestroy: "+str(acceptDestroy))
        logger.info("verbose: "+str(args.verbose))
        logger.info("azSubscriptionId: "+str(azSubscriptionId))
        logger.info("azClientId: "+str(azClientId))
        logger.info("azTenantId: "+str(azTenantId))
        logger.info("================================================")

    # Appel du constructeur
    t = Terraform(azSubscriptionId, azClientId, args.clientSecret, azTenantId, azAccessKey, terraformpath,
                  backendfile, varfiles, logger, applyAutoApprove=autoapprove, variables=variables, planout=outplan,
                  outputazdo=outputAzdo, use_apply=applyterraform, run_output=terraformoutput, terraformversion="0.12.0", useazcli=useazcli)


    currentfolder = os.getcwd()
    os.chdir(terraformpath)

    # Terraform Format
    t.Format()
    
    # Terraform Init
    t.Init()

    # Terraform Validate
    is_valide_code = t.Validate()
    logger.info("Validate return code: {}".format(is_valide_code))

    if(is_valide_code in [1]):
        sys.exit("Error in Terraform validate")
    else:

        if(args.destroy == True):
            # Terraform Destroy
            t.Destroy()
        else:

            # Terraform Plan
            plan_ret_code = t.Plan()
            logger.info("Plan return code: {}".format(plan_ret_code))

            # Si erreur dans le plan de Terraform
            if(plan_ret_code in [1]):
                sys.exit("Error in Terraform plan")
            else:
                if(plan_ret_code in [2]):  # plan need changes
                    if (t.use_apply == True):
                        terraformdestroy = False  # Does changes need deletes, default false
                        if(acceptDestroy == False):
                            terraformdestroy = t.CheckIfDestroy()  # check dans le plan

                            if(terraformdestroy == False):
                                # Terraform Apply

                                apply_ret_code = t.Apply()
                                logger.info(
                                    "Apply return code: {}".format(apply_ret_code))
                                if(apply_ret_code in [1, 256]):
                                    sys.exit("Error in Terraform apply")

                            else:
                                sys.exit(
                                    "Error Terraform will be destroy resources")

                        if(acceptDestroy == True):
                            # Terraform Apply with acceptDestroy
                            apply_ret_code = t.Apply()
                            logger.info(
                                "Apply return code: {}".format(apply_ret_code))
                            if(apply_ret_code in [1]):
                                sys.exit("Error in Terraform apply")
                    else:
                        logger.info("=> Terraform apply is skipped")

            ret = ""
            if(plan_ret_code in [0, 2]):  # no changes or changes
                # Terraform Output tf => Azure DevOps variables
                if(t.run_output == True):
                    jsonObject = t.Output()
                    azdo.tfoutputtoAzdo(outputAzdo, jsonObject)
                else:
                    logger.info("==> Terraform output is skipped")

            # clean folder
            t.Clean()

    logger.info("====> End Terraform execution")
