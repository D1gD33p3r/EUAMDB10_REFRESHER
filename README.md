# EUAMDB10_REFRESHER

Pipeline automatisé de récupération et de publication de l'indice EUAMDB10
(Natixis, EUR CMS 10Y) : batch quotidien, génération d'un JSON de
consultation, page web statique affichant la dernière valeur (SPOT) et un
historique interactif avec seuils fixes.

**Page publique :** https://d1gd33p3r.github.io/EUAMDB10_REFRESHER/

> ⚠️ Démonstration réalisée dans le cadre d'ateliers d'apprentissage. Ce
> n'est pas un système de production, ni une source officielle de valeurs
> de marché. Voir le bandeau d'avertissement affiché sur la page elle-même,
> et la page officielle de l'indice sur
> [Natixis](https://equityderivatives.natixis.com/fr/indice/euamdb10/).

## Fonctionnement en un coup d'œil

```
Site Natixis (scraping) → scripts/EUAMDB10_DailyBatch_v1.05.py
        → data/EUAMDB10_SPOT.csv, data/EUAMDB10_HISTO.csv
        → scripts/build_frontend_data.py (lit aussi data/EUAMDB10_PARAMS.csv)
        → docs/data/euamdb10.json
        → docs/index.html (servi par GitHub Pages)
```

Orchestré par `.github/workflows/daily.yml` : trois créneaux cron quotidiens
(11:42, 15:47, 19:53 UTC) + déclenchement manuel possible via l'onglet
Actions. Supervision externe par [healthchecks.io](https://healthchecks.io)
(alerte email si aucun run ne réussit sur une journée complète).

## Arborescence

```
data/       CSV bruts (source) + JSON généré (référence)
docs/       Page publiée + copie du JSON réellement servie
scripts/    Récupération Natixis + génération du JSON
.github/    Workflow d'orchestration
```

## Modifier les seuils affichés (SEUIL 1 / SEUIL 2)

Éditer `data/EUAMDB10_PARAMS.csv` (format `param;value`, clés `MIN` et
`MAX`), committer et pousser. Les nouvelles valeurs apparaissent sur la
page publique après le prochain run du workflow (automatique ou déclenché
manuellement depuis l'onglet Actions).

## Documentation complète

Un manuel de référence détaillé (architecture, workshop de reproduction,
code source intégral, dépannage, maintenance, sécurité, décisions
techniques) est disponible séparément :
`EUAMDB10_REFRESHER_Documentation_Complete_v1.3.docx`.
