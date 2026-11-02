"""Run one offline, headless example; does not publish content."""
from dataclasses import asdict
import json
from . import FirstSliceWorkflow, ResearchEvidence, TrendOpportunity


def main() -> None:
    opportunity = TrendOpportunity("demo-001", "Home gardening", "Home gardeners", "operator example")
    evidence = ResearchEvidence("e-001", "demo-001", "operator reference", "Assess local conditions.")
    outcome = FirstSliceWorkflow().execute(
        opportunity, [evidence], title="Garden planning",
        body="Draft an evidence-grounded planning guide.", cited_evidence_ids=["e-001"],
    )
    print(json.dumps(asdict(outcome), indent=2))


if __name__ == "__main__":
    main()
