"""Factuur uitlezen met Claude: pdf of foto erin, gestructureerde gegevens eruit.
Vereist ANTHROPIC_API_KEY in config.env. Zonder sleutel valt de app terug op eenvoudige tekstherkenning."""

import base64
import json
import os

MODEL = "claude-opus-5-5"

SYSTEEM = """Je leest inkomende facturen uit voor de boekhouding van {bedrijf}.
{bedrijf} is de ONTVANGER van de factuur; de leverancier is de partij die de factuur stuurt.
Regels:
- Neem gegevens exact over zoals ze op het document staan. Verzin niets: onbekend = lege tekst of 0.
- Datums in formaat JJJJ-MM-DD. Bedragen in euro als getal met punt als decimaalteken.
- bedrag_excl + btw_bedrag moet bedrag_incl zijn. Bij meerdere btw-tarieven: btw_pct is het hoogste tarief.
- Het IBAN is het rekeningnummer van de leverancier waarop betaald moet worden, niet dat van {bedrijf}.
- betaalwijze: "incasso" als het bedrag automatisch wordt afgeschreven of geïncasseerd, "al_betaald" als
  de factuur al voldaan is (creditcard, iDEAL, "betaald"), anders "overboeking".
- Kies de grootboekrekening die het beste past bij wat er gekocht is.
- zekerheid: 0 tot 1, hoe zeker je bent dat alle velden juist zijn (lager bij slechte scan of twijfel).
- is_factuur is false voor documenten die geen factuur of creditnota zijn (offertes, nieuwsbrieven, aanmaningen zonder nieuwe factuur)."""


def beschikbaar():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _schema(rekeningcodes):
    tekst = {"type": "string"}
    getal = {"type": "number"}
    velden = {
        "is_factuur": {"type": "boolean"},
        "is_creditnota": {"type": "boolean"},
        "leverancier_naam": tekst, "leverancier_iban": tekst, "leverancier_kvk": tekst,
        "leverancier_btw_nummer": tekst, "leverancier_email": tekst,
        "leverancier_adres": tekst, "leverancier_postcode": tekst, "leverancier_plaats": tekst,
        "factuurnummer": tekst, "factuurdatum": tekst, "vervaldatum": tekst,
        "omschrijving": tekst,
        "bedrag_excl": getal, "btw_bedrag": getal, "bedrag_incl": getal,
        "btw_pct": {"type": "integer", "enum": [0, 9, 21]},
        "betalingskenmerk": tekst,
        "betaalwijze": {"type": "string", "enum": ["overboeking", "incasso", "al_betaald"]},
        "grootboekrekening": {"type": "string", "enum": rekeningcodes},
        "zekerheid": getal,
        "opmerkingen": tekst,
    }
    return {"type": "object", "properties": velden, "required": list(velden), "additionalProperties": False}


def lees_factuur(inhoud, mediatype, bedrijfsnaam, rekeningen):
    """rekeningen: lijst van (code, naam). Geeft dict met de velden uit _schema terug."""
    import anthropic

    if mediatype == "application/pdf":
        blok = {"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                               "data": base64.standard_b64encode(inhoud).decode()}}
    elif mediatype in ("image/jpeg", "image/png", "image/gif", "image/webp"):
        blok = {"type": "image", "source": {"type": "base64", "media_type": mediatype,
                                            "data": base64.standard_b64encode(inhoud).decode()}}
    else:
        raise ValueError(f"Bestandstype {mediatype} kan niet automatisch worden gelezen")

    lijst = "\n".join(f"{code} {naam}" for code, naam in rekeningen)
    client = anthropic.Anthropic()
    try:
        antwoord = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=SYSTEEM.format(bedrijf=bedrijfsnaam),
            output_config={"effort": "medium",
                           "format": {"type": "json_schema", "schema": _schema([c for c, _ in rekeningen])}},
            messages=[{"role": "user", "content": [
                blok,
                {"type": "text", "text": f"Lees deze factuur uit. Beschikbare kostenrekeningen:\n{lijst}"},
            ]}],
        )
    except anthropic.AuthenticationError:
        raise ValueError("De ANTHROPIC_API_KEY in config.env is ongeldig")
    except anthropic.RateLimitError:
        raise ValueError("Claude is tijdelijk overbelast; het document wordt later opnieuw geprobeerd")
    except anthropic.APIConnectionError:
        raise ValueError("Geen verbinding met Claude; het document wordt later opnieuw geprobeerd")
    except anthropic.APIStatusError as e:
        raise ValueError(f"Claude gaf een fout ({e.status_code}) bij het uitlezen")

    if antwoord.stop_reason == "refusal":
        raise ValueError("Claude kon dit document niet verwerken")
    if antwoord.stop_reason == "max_tokens":
        raise ValueError("Het antwoord van Claude was onvolledig")
    tekst = next((b.text for b in antwoord.content if b.type == "text"), None)
    if not tekst:
        raise ValueError("Claude gaf geen gegevens terug")
    return json.loads(tekst)
