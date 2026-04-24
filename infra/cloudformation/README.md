# Ruter Chatbot AWS IaC

Dette er en ryddet CloudFormation-pakke for dagens `eu-west-1`-miljø.

Pakken er delt i to:

- `network.yaml`
  - VPC
  - internet gateway
  - route table
  - to public subnets
- `runtime.yaml`
  - ECR repositories
  - ECS cluster
  - runtime-IAM-roller
  - CloudWatch log groups
  - security groups
  - ALB, listeners, rules og target groups
  - ECS task definitions
  - ECS services med ECS-native blue/green
  - autoscaling
- `cicd.yaml`
  - GitHub OIDC provider
  - GitHub deploy-role for Actions

I tillegg finnes det en bootstrap-workflow:

- [bootstrap-aws.yml](/C:/Users/JohanNorlinder/ruter_chatbot/.github/workflows/bootstrap-aws.yml)
  - deployer `runtime.yaml`
  - bygger og pusher de første API- og Chainlit-imagene
  - leser outputs fra runtime-stacken
  - deployer `cicd.yaml`
  - setter repo-variablene `AWS_REGION` og `AWS_ROLE_TO_ASSUME`

## Hvorfor ikke bruke de gamle ECS-console-stackene?

De gamle `ECS-Console-V2-*` stack-templateene beskriver ikke dagens løsning lenger:

- de peker på gamle task definition-revisjoner
- de bruker rolling update i stedet for blue/green
- de mangler dagens ALB-koblinger
- de bruker gammel security group-konfigurasjon

Denne pakken er derfor skrevet ut fra dagens faktiske AWS-oppsett, ikke fra de gamle console-stackene.

## Hva er bevisst tatt med?

- runtime-oppsettet slik det kjører i dag
- test listeners på `9001` og `9002`, fordi ECS-native blue/green faktisk bruker dem
- `GitHubActionsDeployRole`, siden repo + deploy-workflow også skal kunne overleveres

## Hva er bevisst ikke modellert som egne ressurser?

- service-linked IAM-roller som AWS oppretter selv ved behov, for eksempel
  - `AWSServiceRoleForElasticLoadBalancing`
  - `AWSServiceRoleForApplicationAutoScaling_ECSService`
- runtime-state som konkrete target-IP-er i target groups
- gamle ECS-console-stack-artefakter

## Forbedringer sammenlignet med generator-utkastet

- `CONFLUENCE_TOKEN` er modellert som ECS `Secret`, ikke klartekst i task definition
- ECS services er modellert med dagens blue/green-oppsett
- autoscaling er parameterisert
- outputs gir viderebrukbare ARN-er og repository-URI-er

## Filer

- [runtime.yaml](/C:/Users/JohanNorlinder/ruter_chatbot/infra/cloudformation/runtime.yaml)
- [network.yaml](/C:/Users/JohanNorlinder/ruter_chatbot/infra/cloudformation/network.yaml)
- [network.parameters.example.json](/C:/Users/JohanNorlinder/ruter_chatbot/infra/cloudformation/network.parameters.example.json)
- [network.parameters.handoff.json](/C:/Users/JohanNorlinder/ruter_chatbot/infra/cloudformation/network.parameters.handoff.json)
- [runtime.parameters.example.json](/C:/Users/JohanNorlinder/ruter_chatbot/infra/cloudformation/runtime.parameters.example.json)
- [runtime.parameters.handoff.json](/C:/Users/JohanNorlinder/ruter_chatbot/infra/cloudformation/runtime.parameters.handoff.json)
- [cicd.yaml](/C:/Users/JohanNorlinder/ruter_chatbot/infra/cloudformation/cicd.yaml)
- [cicd.parameters.example.json](/C:/Users/JohanNorlinder/ruter_chatbot/infra/cloudformation/cicd.parameters.example.json)
- [cicd.parameters.handoff.json](/C:/Users/JohanNorlinder/ruter_chatbot/infra/cloudformation/cicd.parameters.handoff.json)

## Deploy-rekkefølge

### Anbefalt: bootstrap via GitHub Actions

1. Legg inn repo-secrets:
   - `AWS_BOOTSTRAP_ACCESS_KEY_ID`
   - `AWS_BOOTSTRAP_SECRET_ACCESS_KEY`
   - `AWS_BOOTSTRAP_SESSION_TOKEN` (kun hvis dere bruker midlertidige credentials)
2. Fyll ut `network.parameters.handoff.json` hvis dere vil bruke andre CIDR-er enn default
3. Fyll ut `runtime.parameters.handoff.json`
4. Kjør `Bootstrap AWS environment`-workflowen
5. Workflowen bygger og pusher første image-sett og setter repo-variabler automatisk
6. Deretter kan vanlige deploy-workflows trigges via push til `dev` eller `workflow_dispatch`

### Alternativ: manuell CloudFormation-deploy

1. Deploy `runtime.yaml`
2. Deploy `cicd.yaml`
3. Sett repo-variablene `AWS_REGION` og `AWS_ROLE_TO_ASSUME`

Eksempel med `create-stack`:

```powershell
aws cloudformation create-stack `
  --region eu-west-1 `
  --stack-name ruter-chatbot-runtime `
  --template-file infra/cloudformation/runtime.yaml `
  --parameters file://infra/cloudformation/runtime.parameters.example.json `
  --capabilities CAPABILITY_NAMED_IAM
```

```powershell
aws cloudformation create-stack `
  --region eu-west-1 `
  --stack-name ruter-chatbot-cicd `
  --template-file infra/cloudformation/cicd.yaml `
  --parameters file://infra/cloudformation/cicd.parameters.example.json `
  --capabilities CAPABILITY_NAMED_IAM
```

Hvis stacken allerede finnes, bruk `update-stack` med samme parameterfil.

## Parameterfiler

- `*.example.json`
  - viser et realistisk eksempel basert på dagens miljø
- `*.handoff.json`
  - ment for overlevering til et annet team eller en annen AWS-konto
  - bruker `REPLACE_ME` bare på feltene som faktisk må endres

## Viktige runtime-parametere

- `VpcId`
- `AlbSubnetIds`
- `ServiceSubnetIds`
- `AllowedIngressCidr1` ... `AllowedIngressCidr6`
- `ConfluenceEmail`
- `ConfluenceTokenSecretArn`
- `ConfluenceToken`
- `ApiImageUri`
- `ChainlitImageUri`
- `ApiMinCapacity`, `ApiMaxCapacity`
- `ChainlitMinCapacity`, `ChainlitMaxCapacity`
- `ApiCpuTargetValue`, `ApiMemoryTargetValue`
- `ChainlitCpuTargetValue`, `ChainlitMemoryTargetValue`

## Viktige CI/CD-parametere

- `GitHubRepository`
- `DevBranchName`
- `MainBranchName`
- `TaskExecutionRoleArn`
- `BedrockTaskRoleArn`

## Hvor finner vi parameterverdiene?

For dette miljøet kjenner vi allerede mange av dem fra dagens AWS-oppsett:

- `VpcId`
  - dagens verdi: `vpc-08a441e3593d0da72`
  - finnes i `VPC`-kolonnen på ECS service, ALB eller security group
- `AlbSubnetIds`
  - dagens verdier: `subnet-045fd688267d0da55`, `subnet-0580a22b36150a01e`
  - finnes på ALB under `Network mapping`
- `ServiceSubnetIds`
  - dagens verdier: `subnet-045fd688267d0da55`, `subnet-0580a22b36150a01e`
  - finnes på ECS service under `Configuration and networking`
- `ApiImageUri`
  - nåværende eksempel: `796576079636.dkr.ecr.eu-west-1.amazonaws.com/ruter-chatbot:<tag>`
  - finnes i ECR eller i ECS task definition
- `ChainlitImageUri`
  - nåværende eksempel: `796576079636.dkr.ecr.eu-west-1.amazonaws.com/ruter-chainlit:<tag>`
  - finnes i ECR eller i ECS task definition
- `ConfluenceEmail`
  - finnes i dagens task definitions / ECS environment configuration
- ingress-CIDR-ene
  - finnes i `ruter-alb-sg`

Kort sagt:

- nettverksverdier hentes fra ECS/ALB/EC2-konsollen
- image-URI-er hentes fra ECR eller task definitions
- applikasjonsverdier hentes fra dagens ECS-konfig eller teamets hemmelighetshåndtering

## Hva må mottakerteamet faktisk fylle ut?

I en ny AWS-konto er det normalt bare disse feltene som må erstattes i handoff-filene:

### runtime.parameters.handoff.json

- `ConfluenceEmail`
- enten `ConfluenceToken` eller `ConfluenceTokenSecretArn`
- `ApiImageUri`
- `ChainlitImageUri`

Ved bootstrap-veien blir `VpcId`, `AlbSubnetIds` og `ServiceSubnetIds` automatisk overstyrt fra `network.yaml`.
De tre feltene er bare relevante hvis noen deployer `runtime.yaml` manuelt uten bootstrap-workflowen.

### cicd.parameters.handoff.json

- `GitHubRepository`
- `TaskExecutionRoleArn`
- `BedrockTaskRoleArn`

Resten kan ofte stå på default i templaten.

### network.parameters.handoff.json

Denne kan som regel brukes som den er.
Det eneste mottakerteamet trenger å vurdere er om de vil beholde default-CIDR-ene eller bytte dem.

## Hva er fortsatt ikke "fra helt tom konto"?

Denne pakken automatiserer nå også nettverksfundamentet i standardvarianten.
Det som fortsatt må leveres inn utenfra er hovedsakelig:

- bootstrap-credentials i GitHub secrets
- Confluence-verdier
- ønsket GitHub-repository-navn

## Secrets Manager er ikke et krav

`runtime.yaml` støtter nå to måter å sette `CONFLUENCE_TOKEN` på:

1. `ConfluenceTokenSecretArn`
   - bruk denne hvis teamet vil bruke Secrets Manager eller SSM Parameter Store
2. `ConfluenceToken`
   - vanlig `NoEcho`-parameter
   - dette matcher dagens enklere oppsett bedre

Dere skal normalt bruke én av dem, ikke begge.

## Overleveringsnotat

Dette er en god basis for overlevering, men neste team bør fortsatt vurdere:

- om `CONFLUENCE_EMAIL` også skal flyttes til Secrets Manager eller SSM
- om ingress-CIDR-er bør modelleres mer fleksibelt enn seks eksplisitte parametere
- om ECS-tasker skal flyttes til private subnets med NAT/VPC endpoints i stedet for public IP
- om image promotion skal knyttes tettere til release-prosessen
