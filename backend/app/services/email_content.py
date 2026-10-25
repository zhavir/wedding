"""Code-owned stationery; invitation messages are database-owned."""

CONTENT = {
    "en": {
        "names": ["Andrea", "Sara"],
        "date": "2027-05-20T16:30:00+02:00",
        "venue": "Villa Valentina",
        "address": "Via Donizetti 17, 21049 Tradate (VA), Italy",
        "contactEmail": "hello@example.com",
        "email": {
            "subject": "You’re invited to our wedding",
            "heading": "It wouldn’t be the same without you.",
            "intro": "We would love you to join us for our next chapter. Open your "
            "invitation to RSVP and share memories.",
            "button": "Open your invitation",
            "footer": "This personal link signs you in. Please keep it private.",
        },
        "witnessEmail": {
            "subject": "Will you be our witness?",
            "heading": "By our side, for our next chapter.",
            "intro": "We would love you to stand beside us as our wedding "
            "witness. Open your personal invitation to confirm your "
            "role, attendance and guest details.",
            "button": "Open your witness invitation",
            "footer": "This personal link signs you in. Please keep it private.",
        },
        "confirmationEmail": {
            "subject": "Thank you — save our wedding date!",
            "eyebrow": "SAVE THE DATE · THANK YOU",
            "intro": "thank you for saying yes! We cannot wait to celebrate our wedding with you.",
            "calendarHelp": "Open the attached .ics file to add our wedding "
            "to your calendar. Arrive at 16:00; the "
            "ceremony begins at 16:30.",
            "button": "Visit our wedding website",
        },
        "dateLabel": "20 May 2027",
        "location": "Tradate, Varese · Italy",
        "labels": {
            "invited": "YOU’RE INVITED",
            "dear": "Dear",
            "gallery": "Open the photo gallery",
            "codeHelp": "Or enter this code on the website to RSVP or upload photos.",
            "questions": "Questions?",
            "signature": "WITH ALL OUR LOVE",
            "chapter": "THE NEXT CHAPTER",
        },
    },
    "it": {
        "names": ["Andrea", "Sara"],
        "date": "2027-05-20T16:30:00+02:00",
        "venue": "Villa Valentina",
        "address": "Via Donizetti 17, 21049 Tradate (VA), Italy",
        "contactEmail": "hello@example.com",
        "email": {
            "subject": "Sei invitato al nostro matrimonio",
            "heading": "Non sarebbe lo stesso senza di te.",
            "intro": "Saremmo felici di averti con noi per il nostro nuovo capitolo. "
            "Apri il tuo invito per rispondere e condividere i ricordi.",
            "button": "Apri il tuo invito",
            "footer": "Questo link personale permette di accedere. Tienilo privato.",
        },
        "witnessEmail": {
            "subject": "Vuoi essere al nostro fianco come testimone?",
            "heading": "Al nostro fianco, nel nostro nuovo capitolo.",
            "intro": "Ci piacerebbe averti al nostro fianco come testimone di "
            "nozze. Apri il tuo invito personale per confermare il "
            "ruolo, la presenza e i dettagli degli ospiti.",
            "button": "Apri il tuo invito da testimone",
            "footer": "Questo link personale permette di accedere. Tienilo privato.",
        },
        "confirmationEmail": {
            "subject": "Grazie — segna la data del nostro matrimonio!",
            "eyebrow": "SEGNA LA DATA · GRAZIE",
            "intro": "grazie per il tuo sì! Non vediamo l’ora di "
            "festeggiare il nostro matrimonio insieme a te.",
            "calendarHelp": "Apri il file .ics allegato per aggiungere il "
            "matrimonio al calendario. Arrivo alle 16:00; "
            "cerimonia alle 16:30.",
            "button": "Visita il sito del matrimonio",
        },
        "dateLabel": "20 maggio 2027",
        "location": "Tradate, Varese · Italia",
        "labels": {
            "invited": "SEI INVITATO",
            "dear": "Ciao",
            "gallery": "Apri la galleria fotografica",
            "codeHelp": "Oppure inserisci questo codice sul sito per rispondere o "
            "caricare le foto.",
            "questions": "Domande?",
            "signature": "CON TUTTO IL NOSTRO AMORE",
            "chapter": "IL PROSSIMO CAPITOLO",
        },
    },
}

ITALIAN_PLURAL = {
    "email": {
        "subject": "Siete invitati al nostro matrimonio",
        "heading": "Non sarebbe lo stesso senza di voi.",
        "intro": "Saremmo felici di avervi con noi per il nostro nuovo capitolo. Aprite il vostro invito per rispondere e condividere i ricordi.",
        "button": "Aprite il vostro invito",
        "footer": "Questo link personale permette di accedere. Tenetelo privato.",
    },
    "labels": {
        "invited": "SIETE INVITATI",
        "gallery": "Aprite la galleria fotografica",
        "codeHelp": "Oppure inserite questo codice sul sito per rispondere o caricare le foto.",
    },
    "confirmationEmail": {
        "subject": "Grazie — segnate la data del nostro matrimonio!",
        "intro": "grazie per il vostro sì! Non vediamo l’ora di festeggiare il nostro matrimonio insieme a voi.",
        "calendarHelp": "Aprite il file .ics allegato per aggiungere il matrimonio al calendario. Arrivo alle 16:00; cerimonia alle 16:30.",
        "button": "Visitate il sito del matrimonio",
    },
}


def participant_copy(wedding: dict, language: str, count: int) -> dict:
    from copy import deepcopy

    result = deepcopy(wedding)
    if language == "it" and count > 1:
        for section, values in ITALIAN_PLURAL.items():
            result[section].update(values)
    return result
