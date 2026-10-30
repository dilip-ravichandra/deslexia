import json
from pathlib import Path

from playwright.sync_api import sync_playwright


root = Path(__file__).resolve().parents[2]
profile = {"id": "learner-1", "alias": "Test learner", "created_at": "2026-10-18T10:00:00Z"}
state = {"need_estimates": {"VOCABULARY": 0.6, "SYNTACTIC": 0.3, "CONCEPTUAL": 0.1}}
evidence = {
    "profiles": [profile],
    "selected": profile["id"],
    "profile": profile,
    "survey": {"difficulties": ["VOCABULARY"], "preferred_style": "steps", "study_languages": ["en"]},
    "metrics": {
        "sessions": 1,
        "support_decisions": 1,
        "explicit_requests": {"VOCABULARY": 1, "SYNTACTIC": 0},
        "feedback": {"helped": 0, "not_helpful": 0},
    },
    "states": {"en": state},
    "events": [{
        "id": "event-1", "kind": "help_request", "language": "en",
        "created_at": "2026-10-18T10:05:00Z", "payload": {"span": "shoot"},
        "reason": "Learner explicitly requested word help.",
        "before_state": {"need_estimates": {"VOCABULARY": 0.4, "SYNTACTIC": 0.4}},
        "after_state": {"need_estimates": {"VOCABULARY": 0.6, "SYNTACTIC": 0.3}},
    }],
    "routes": [{
        "selected": "VOCABULARY", "style": "steps", "language": "en", "span": "shoot",
        "evidence": {"source": "explicit_choice", "explanation_quality": {"summary": "A young plant stem."}},
    }],
}
research = {"routing_runs": [{
    "run_id": "test-run", "baseline": {"models": {"tfidf_logreg": {"test": {"macro_f1": 0.5}}}},
    "distilbert": {"test": {"macro_f1": 0.6}},
    "distilbert_features": {"test": {"macro_f1": 0.7}},
}]}
overview = {"profiles": 1, "sessions": 1, "support_responses": 1,
            "explicit_requests": {"VOCABULARY": 1, "SYNTACTIC": 0},
            "optional_feedback": {"helped": 0, "not_helpful": 0},
            "note": "Requests are choices, not mistakes."}
script = """const evidence = %s;
const research = %s;
const overview = %s;
window.fetch = async path => ({ok: true, json: async () =>
  path.includes('dataset-status') ? {sources:[{id:'CompLex',role:'Lexical reference, not routing labels',expected_files:4,verified_files:4,problems:[]}],note:'Public references are not support-routing labels.'} :
  path.includes('model-status') ? {services:{generation:{ready:true},speech:{en:{ready:true}}},human_routing:{available:false}} :
  path.includes('research-evidence') ? research :
  path.includes('learner-overview') ? overview :
  path.includes('profile_id=') ? evidence : {profiles: evidence.profiles, selected: null}
});""" % (json.dumps(evidence), json.dumps(research), json.dumps(overview))

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    for width in (1280, 375):
        page = browser.new_page(viewport={"width": width, "height": 850})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.add_init_script(script)
        page.goto((root / "FRONTEND" / "research-demo.html").as_uri())
        page.locator("#before-after .change-row").first.wait_for()
        assert page.locator('#overall-requests .bar').count() == 1
        assert page.locator('#route-flow .route-step').count() == 4
        assert page.locator("#requests .bar").count() == 1
        assert page.locator("#evaluations .bar").count() == 3
        assert page.locator("#shown").inner_text().count("shoot") == 1
        page.locator('#methods summary').click()
        page.get_by_text('CompLex: 4/4 pinned files verified', exact=False).wait_for()
        assert 'speech en: installed' in page.locator('#installation').inner_text()
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        assert not errors, errors
        page.close()
    browser.close()
print("Research lab desktop and mobile smoke checks passed.")
