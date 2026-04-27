# Ruter Chatbot AWS setup

Denne mappen er laget for teamet som får repoet overlevert og skal sette opp miljøet i egen AWS-konto.

## Filer

- [network.yaml](network.yaml)
- [runtime.yaml](runtime.yaml)
- [cicd.yaml](cicd.yaml)
- [network.parameters.handoff.json](network.parameters.handoff.json)
- [runtime.parameters.handoff.json](runtime.parameters.handoff.json)
- [cicd.parameters.handoff.json](cicd.parameters.handoff.json)
- [bootstrap-aws.yml](../../.github/workflows/bootstrap-aws.yml)

`*.handoff.json` er filene som skal brukes ved overlevering. `*.example.json` er bare referanser.

## Hva må fylles ut

### `network.parameters.handoff.json`

Denne kan normalt brukes som den er. Endre bare hvis dere vil bruke andre CIDR-er enn default.

### `runtime.parameters.handoff.json`

Dere må fylle ut:

- `ConfluenceEmail`
- repo-secret `CONFLUENCE_TOKEN` i GitHub

`ConfluenceToken` skal stå tom i parameterfilen. Workflowen setter den fra repo-secret `CONFLUENCE_TOKEN` under bootstrap.

`ApiImageUri` og `ChainlitImageUri` kan stå tomme. Hvis de står tomme, utleder `runtime.yaml` automatisk:

- `${account}.dkr.ecr.${region}.amazonaws.com/ruter-chatbot:prod-latest`
- `${account}.dkr.ecr.${region}.amazonaws.com/ruter-chainlit:prod-latest`

### `cicd.parameters.handoff.json`

Det viktigste her er:

- `GitHubRepository`

## Anbefalt: bootstrap via GitHub Actions

Dette er anbefalt oppstartsspor for teamet som får repoet overlevert.

Flyten er:

1. Fyll ut `infra/cloudformation/runtime.parameters.handoff.json`
2. Endre `infra/cloudformation/network.parameters.handoff.json` bare hvis dere vil bruke andre nettverks-CIDR-er enn default
3. Legg inn disse repo-secretsene i GitHub:
   - `AWS_BOOTSTRAP_ACCESS_KEY_ID`
   - `AWS_BOOTSTRAP_SECRET_ACCESS_KEY`
   - `AWS_BOOTSTRAP_SESSION_TOKEN` hvis dere bruker midlertidige credentials
   - `CONFLUENCE_TOKEN`
4. Gå til GitHub-repoet
5. Åpne `Actions`
6. Velg [bootstrap-aws.yml](../../.github/workflows/bootstrap-aws.yml)
7. Klikk `Run workflow`
8. Velg branch
9. Start workflowen i GitHub UI

Når workflowen kjører, gjør den dette:

1. Oppretter nettverket fra `network.yaml`
2. Oppretter runtime foundation fra `runtime.yaml`
3. Bygger og pusher første API- og Chainlit-image til ECR
4. Aktiverer ECS services, ALB, blue/green og autoscaling
5. Oppretter CI/CD-oppsettet fra `cicd.yaml`
6. Setter repo-variablene `AWS_REGION` og `AWS_ROLE_TO_ASSUME`

Etter dette bruker vanlige deploy-workflows OIDC, ikke bootstrap-secrets.

## Etter bootstrap

Når bootstrap er ferdig, fungerer disse workflowene:

- [deploy-api.yml](../../.github/workflows/deploy-api.yml)
- [deploy-chainlit.yml](../../.github/workflows/deploy-chainlit.yml)

De kan trigges ved:

- push til `dev`
- eller `workflow_dispatch`
