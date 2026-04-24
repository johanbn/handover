# Ruter Chatbot AWS setup

Denne mappen er laget for teamet som får repoet overlevert og skal sette opp miljøet i egen AWS-konto.

## Filer

- [network.yaml](/C:/Users/JohanNorlinder/ruter_chatbot/infra/cloudformation/network.yaml)
- [runtime.yaml](/C:/Users/JohanNorlinder/ruter_chatbot/infra/cloudformation/runtime.yaml)
- [cicd.yaml](/C:/Users/JohanNorlinder/ruter_chatbot/infra/cloudformation/cicd.yaml)
- [network.parameters.handoff.json](/C:/Users/JohanNorlinder/ruter_chatbot/infra/cloudformation/network.parameters.handoff.json)
- [runtime.parameters.handoff.json](/C:/Users/JohanNorlinder/ruter_chatbot/infra/cloudformation/runtime.parameters.handoff.json)
- [cicd.parameters.handoff.json](/C:/Users/JohanNorlinder/ruter_chatbot/infra/cloudformation/cicd.parameters.handoff.json)
- [bootstrap-aws.yml](/C:/Users/JohanNorlinder/ruter_chatbot/.github/workflows/bootstrap-aws.yml)

`*.handoff.json` er filene som skal brukes ved overlevering. `*.example.json` er bare referanser.

## To måter å bootstrappe miljøet på

### Alternativ A: Lokalt fra egen maskin

Dette er hovedsporet hvis dere bruker vanlig AWS-auth, for eksempel:

- `~/.aws/credentials`
- named profile
- AWS SSO

Brukeren dere autentiserer som må kunne opprette CloudFormation-stacks, IAM-roller, ECR, ECS, ALB og GitHub OIDC-relatert IAM-oppsett.

### Alternativ B: Via GitHub Actions

Hvis dere vil kjøre bootstrap fra GitHub Actions, må dere legge inn disse repo-secretsene:

- `AWS_BOOTSTRAP_ACCESS_KEY_ID`
- `AWS_BOOTSTRAP_SECRET_ACCESS_KEY`
- `AWS_BOOTSTRAP_SESSION_TOKEN`

`AWS_BOOTSTRAP_SESSION_TOKEN` trengs bare hvis dere bruker midlertidige credentials.

Dette er bare for bootstrap. Vanlige deploy-workflows bruker OIDC etterpå.

## Hva dere må fylle ut

### `network.parameters.handoff.json`

Denne kan normalt brukes som den er.

Endre bare hvis dere vil bruke andre CIDR-er enn default.

### `runtime.parameters.handoff.json`

Dere må fylle ut:

- `ConfluenceEmail`
- enten `ConfluenceToken` eller `ConfluenceTokenSecretArn`

Image-URI-ene trenger dere normalt ikke å fylle ut.

Hvis `ApiImageUri` og `ChainlitImageUri` står tomme, utleder `runtime.yaml` automatisk:

- `${account}.dkr.ecr.${region}.amazonaws.com/ruter-chatbot:prod-latest`
- `${account}.dkr.ecr.${region}.amazonaws.com/ruter-chainlit:prod-latest`

Dere kan fortsatt sette `ApiImageUri` og `ChainlitImageUri` eksplisitt senere hvis dere vil overstyre dette.

### `cicd.parameters.handoff.json`

Det viktigste her er:

- `GitHubRepository`

Bootstrap-workflowen leser rolle-ARN-er fra runtime-stacken automatisk.

## Anbefalt rekkefølge

### Hvis dere bootstrapper lokalt

1. Fyll ut `runtime.parameters.handoff.json`
2. Juster `network.parameters.handoff.json` bare hvis dere vil bruke andre CIDR-er
3. Deploy `network.yaml`
4. Deploy `runtime.yaml`
5. Bygg og push første API- og Chainlit-image til ECR
6. Deploy eller oppdater `runtime.yaml` igjen hvis dere vil bruke andre image-tagger enn default
7. Deploy `cicd.yaml`
8. Sett GitHub repo-variablene:
   - `AWS_REGION`
   - `AWS_ROLE_TO_ASSUME`

### Hvis dere bootstrapper via GitHub Actions

Kjør [Bootstrap AWS environment](/C:/Users/JohanNorlinder/ruter_chatbot/.github/workflows/bootstrap-aws.yml).

Workflowen gjør dette:

1. deployer `network.yaml`
2. henter VPC- og subnet-verdier fra network-stacken
3. deployer `runtime.yaml` i foundation-modus
4. bygger og pusher første API- og Chainlit-image
5. oppdaterer `runtime.yaml` til full service-konfig
6. deployer `cicd.yaml`
7. setter repo-variablene:
   - `AWS_REGION`
   - `AWS_ROLE_TO_ASSUME`

## Etter bootstrap

Når bootstrap er ferdig, fungerer disse workflowene:

- [deploy-api.yml](/C:/Users/JohanNorlinder/ruter_chatbot/.github/workflows/deploy-api.yml)
- [deploy-chainlit.yml](/C:/Users/JohanNorlinder/ruter_chatbot/.github/workflows/deploy-chainlit.yml)

De kan trigges ved:

- push til `dev`
- eller `workflow_dispatch`

## Viktige noter

- `runtime.yaml` bruker ECS-native blue/green
- test listeners på `9001` og `9002` er en del av løsningen
- `runtime.yaml` støtter både secret ARN og vanlig `NoEcho`-parameter for `CONFLUENCE_TOKEN`
- bootstrap lager ikke GitHub-repoet; repoet må allerede finnes

## Kort oppsummert

For mottakerteamet er flyten:

1. få repoet
2. fylle ut `runtime.parameters.handoff.json`
3. eventuelt justere `network.parameters.handoff.json`
4. bootstrappe miljøet lokalt eller via GitHub Actions
5. bruke vanlige deploy-workflows videre
