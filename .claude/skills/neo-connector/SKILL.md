---
name: neo-connector
description: Régénère NEO_CONNECTOR.md (manifeste de connexion pour NeoBot) en auditant ce repo.
---

Tu es en train d'auditer CE repo (WhalegodTG) pour produire un manifeste de connexion
machine-lisible destiné à NeoBot (l'agent Neo de SoClose). NeoBot doit pouvoir appeler
TOUTES les fonctionnalités HTTP exposées par ce projet sans deviner -- ou comprendre
clairement qu'il n'y en a pas. Ne rien inventer : tout doit être prouvé par le code. Si
une info est absente, écris "UNKNOWN -- <fichier où elle devrait être>".

RAPPEL SUR CE REPO : WhalegodTG est un bot Telegram + poller asyncio. Il CONSOMME des API
externes (Helius, Alchemy, Etherscan, DexScreener, Jupiter, CoinGecko) et n'expose AUCUNE
API HTTP applicative. Les deux seuls serveurs aiohttp entrants (`bot/main.py`) sont :
`GET /health` (port 8080) et `POST /webhook/helius` (port WEBHOOK_PORT, récepteur du
callback Helius). Aucun des deux n'a d'auth ni n'est destiné à être appelé par Neo.

Étapes :
1. Détecte le type de projet et le framework (ici : Python, python-telegram-bot + aiohttp.web).
2. Trouve TOUTES les routes/endpoints HTTP entrants : `app.router.add_get/add_post`,
   `web.Application`, `web.TCPSite` dans `bot/main.py`. Détecte aussi webhooks, SSE/WS, cron
   (APScheduler `scheduler.add_job`), queues. NE confonds PAS les appels SORTANTS
   (session.get/post vers Helius/Alchemy/etc.) avec des endpoints exposés.
3. Pour chaque endpoint entrant, extrait : méthode, chemin, port, auth (header/secret/clé),
   params d'entrée (body/query, types, requis/optionnels), forme de la réponse, codes
   d'erreur, et s'il déclenche du traitement async (ex: `asyncio.create_task`).
4. Liste les variables d'env nécessaires (noms uniquement, JAMAIS les valeurs) depuis
   `bot/config.py` et `.env.example`.
5. Détecte la base URL de prod (README, docker-compose, deploy.sh, CLAUDE.md). Ici : UNKNOWN
   (self-hosted, pas de domaine public ; WEBHOOK_HOST est l'adresse donnée À Helius).
6. Note les flux multi-étapes en pseudo-séquence (ici : webhook push Solana, polling ETH).
7. Conclus explicitement si le service DOIT ou NE DOIT PAS être branché comme tool HTTP Neo.

Écris le résultat dans NEO_CONNECTOR.md à la racine, AVEC EXACTEMENT cette structure :

# NEO_CONNECTOR -- <nom du projet>
- service: <slug>
- base_url_prod: <url ou UNKNOWN>
- auth: <type: x-api-key | Bearer | cookie | none> ; header: <nom> ; env_var: <NOM_VAR>
- env_required: [LISTE_DES_NOMS]
- generated_at: <laisser vide, NeoBot le datera>

## Endpoints
Pour CHAQUE endpoint, un bloc :
### <METHOD> <path>
- auth: <oui/non + comment>
- async: <true/false>
- input: <param | type | requis | description>
- output: <forme JSON résumée>
- errors: <codes + sens>
- example_curl: <exemple réel d'appel>

## Flows
Séquences multi-étapes.

## Gaps
Tout ce qui est UNKNOWN ou ambigu, avec le fichier à vérifier.

Termine par un récap : nombre d'endpoints trouvés, combien utilisables comme tools Neo
(ici : 0), et la recommandation de NE PAS câbler ce repo en tools HTTP.
