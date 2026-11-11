# Tempo AI for Home Assistant

Home Assistant integration for [Tempo AI](https://github.com/lgm42/tempo-ai), a local AI that
forecasts the French **Tempo** electricity color (blue / white / red) **2 to 4 days ahead**. RTE only
publishes the next day.

The integration reads everything from the Tempo AI server with one REST call every 10 minutes:

- the colors of today, tomorrow, D+2, D+3 and D+4, with probabilities;
- the white and red days left in the season;
- the success rates the server measures on its own forecasts.

> 🇫🇷 Intégration Home Assistant pour Tempo AI : couleurs Tempo prévues à J+2, J+3 et J+4,
> jours restants et taux de réussite. Les entités sont traduites en français.

## Requirements

A running [Tempo AI](https://github.com/lgm42/tempo-ai) server, version 0.1.0 or later. It can run
as a Docker container or as a TrueNAS app, and it listens on port 31090 by default. Home Assistant
2026.10 or later.

## Installation

### HACS

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=lgm42&repository=ha-tempo-ai&category=integration)

1. In HACS, open ⋮ → **Custom repositories**.
2. Add `https://github.com/lgm42/ha-tempo-ai`, with type **Integration**.
3. Install **Tempo AI**, then restart Home Assistant.

### Manual

Copy `custom_components/tempo_ai` into the `custom_components` folder of your configuration, then
restart Home Assistant.

## Configuration

**Settings → Devices & services → Add integration → Tempo AI**, then:

- **URL:** the server address, for example `http://192.168.1.10:31090`.
- **API token:** only if `TEMPO_API_TOKEN` is set on the server. The buttons need it in that case.

To change the URL or the token later, use **Reconfigure** on the integration.

## Entities

All entities belong to one **Tempo AI** service device.

| Entity | Description |
|---|---|
| Color today / tomorrow | `blue`, `white` or `red`. Attribute `source` tells whether the color is official (`rte`) or forecast (`model`). |
| Color D+2 / D+3 / D+4 | Forecast color. Attributes: `date`, `probability_blue`, `probability_white`, `probability_red` (%), `net_load_mw`, `score`, `threshold_white`, `threshold_red`. |
| White / red probability D+2…D+4 | The same probabilities as sensors, to keep a history (disabled by default). |
| White days left / Red days left | Remaining days in the season (out of 43 white and 22 red). |
| Success rate, this season, this month, last 7 days | Share of right forecasts (%). Attributes: `correct`, `total`, per-horizon rates, red days found. |
| Success rate D+2 / D+3 / D+4 | Overall rate per horizon. |
| Red day expected / White day expected | On when one of the next 4 days has that color. Attribute `dates`. |
| Recompute forecast (button) | Collects fresh data and recomputes now (a few seconds). |
| Retrain models (button) | Retrains the models in the background (about a minute). |
| Diagnostics | Status, last training, forecast time, next daily run, tracking start, forecasts evaluated. |

The success rates fill up over time. The server stores one forecast per day and compares it with
the real color once RTE publishes it, so the first D+2 result comes two days after installation.

## Examples

Notification when a red day shows up in the forecast:

```yaml
automation:
  - alias: Tempo red day expected
    triggers:
      - trigger: state
        entity_id: binary_sensor.tempo_ai_red_day_expected
        to: "on"
    actions:
      - action: notify.notify
        data:
          message: >-
            Red Tempo day expected on
            {{ state_attr('binary_sensor.tempo_ai_red_day_expected', 'dates') | join(', ') }}
```

Dashboard card:

```yaml
type: entities
title: Tempo
entities:
  - sensor.tempo_ai_color_tomorrow
  - sensor.tempo_ai_color_d_2
  - sensor.tempo_ai_color_d_3
  - sensor.tempo_ai_color_d_4
  - sensor.tempo_ai_red_days_left
  - sensor.tempo_ai_success_rate
```

Entity IDs follow the language of your Home Assistant at installation time. In French, for example,
they are `sensor.tempo_ai_couleur_j_2` and `binary_sensor.tempo_ai_jour_rouge_prevu`.

## Development

The tests use
[pytest-homeassistant-custom-component](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component)
and need Linux and Python 3.14:

```bash
pip install -r requirements_test.txt
pytest
```

The CI also runs `hassfest` and the HACS validation.

## License

MIT. This project is not affiliated with EDF or RTE. Forecasts are estimates: always check the
official color.
