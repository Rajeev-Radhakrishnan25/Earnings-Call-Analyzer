"""
Generate RBC (Royal Bank of Canada) sample transcripts.

RBC trades on NYSE as RY and files with the SEC as a foreign
private issuer. This script creates realistic earnings call
transcripts covering RBC's key business segments.

Usage:
    python3 scripts/generate_rbc_data.py
"""

import json
import random
from pathlib import Path

RBC = {
    "ticker": "RY",
    "company_name": "Royal Bank of Canada",
    "cik": "0001000275",
    "sector": "Finance",
    "exchange": "NYSE",
    "is_sp500": False,
    "ceo": "Dave McKay",
    "cfo": "Katherine Gibson",
}

QUARTERS = [
    ("Q1", 2024), ("Q2", 2024), ("Q3", 2024), ("Q4", 2024),
    ("Q1", 2025), ("Q2", 2025), ("Q3", 2025), ("Q4", 2025),
]

ANALYSTS = [
    ("Meny Grauman", "Scotiabank"),
    ("Gabriel Dechaine", "National Bank Financial"),
    ("Ebrahim Poonawala", "Bank of America"),
    ("John Aiken", "Barclays"),
    ("Sohrab Movahedi", "BMO Capital Markets"),
]

# RBC-specific content by quarter with varied sentiment
QUARTER_DATA = {
    ("Q1", 2024): {
        "sentiment": "positive",
        "revenue": 14.8,
        "net_income": 3.9,
        "cet1": 14.1,
        "roe": 15.2,
        "pcl": 813,
        "highlights": [
            "strong performance in Capital Markets with trading revenue up 18%",
            "successful integration of HSBC Canada continues ahead of schedule",
            "digital banking adoption reached 6.2 million active users",
            "wealth management AUM grew to $1.2 trillion",
        ],
        "ceo_tone": "confident",
        "themes": ["HSBC Canada integration", "technology investment", "Capital Markets strength"],
    },
    ("Q2", 2024): {
        "sentiment": "positive",
        "revenue": 15.1,
        "net_income": 4.1,
        "cet1": 13.8,
        "roe": 16.0,
        "pcl": 920,
        "highlights": [
            "record revenue quarter driven by Capital Markets and Wealth Management",
            "HSBC Canada integration milestones achieved in retail branch conversion",
            "AI and machine learning investments driving operational efficiency gains",
            "Canadian personal banking mortgage portfolio grew 5% year over year",
        ],
        "ceo_tone": "bullish",
        "themes": ["AI and digital transformation", "HSBC synergies", "record results"],
    },
    ("Q3", 2024): {
        "sentiment": "neutral",
        "revenue": 14.5,
        "net_income": 3.6,
        "cet1": 13.5,
        "roe": 14.8,
        "pcl": 1050,
        "highlights": [
            "solid results despite elevated provisions for credit losses",
            "Capital Markets revenue normalized from prior quarter highs",
            "continued investment in technology platform modernization",
            "Canadian housing market showed signs of stabilization",
        ],
        "ceo_tone": "measured",
        "themes": ["credit quality vigilance", "technology modernization", "housing market"],
    },
    ("Q4", 2024): {
        "sentiment": "positive",
        "revenue": 15.6,
        "net_income": 4.3,
        "cet1": 13.9,
        "roe": 16.5,
        "pcl": 890,
        "highlights": [
            "strong finish to fiscal year with record full-year earnings",
            "HSBC Canada integration substantially complete, ahead of cost synergy targets",
            "launched new AI-powered advisory tools for wealth management clients",
            "provisions stabilizing as credit environment improves",
        ],
        "ceo_tone": "confident",
        "themes": ["record annual results", "HSBC integration complete", "AI advisory tools"],
    },
    ("Q1", 2025): {
        "sentiment": "bullish",
        "revenue": 16.2,
        "net_income": 4.6,
        "cet1": 14.2,
        "roe": 17.1,
        "pcl": 780,
        "highlights": [
            "strong start to fiscal 2025 with double-digit earnings growth",
            "Capital Markets had its best Q1 in five years",
            "technology spending up 12% year over year focused on AI and cloud",
            "full HSBC Canada synergies now being realized across all segments",
        ],
        "ceo_tone": "bullish",
        "themes": ["earnings momentum", "technology acceleration", "synergy realization"],
    },
    ("Q2", 2025): {
        "sentiment": "positive",
        "revenue": 16.8,
        "net_income": 4.8,
        "cet1": 14.5,
        "roe": 17.5,
        "pcl": 720,
        "highlights": [
            "continued momentum across all business segments",
            "digital-first strategy delivering measurable client experience improvements",
            "Quantitative Technology Services team expanding AI capabilities",
            "wealth management net new asset flows at record levels",
        ],
        "ceo_tone": "confident",
        "themes": ["QTS and AI capabilities", "digital strategy", "wealth growth"],
    },
    ("Q3", 2025): {
        "sentiment": "positive",
        "revenue": 16.5,
        "net_income": 4.5,
        "cet1": 14.3,
        "roe": 16.8,
        "pcl": 750,
        "highlights": [
            "resilient performance in a mixed macroeconomic environment",
            "investment in AI and machine learning across trading and risk management",
            "Halifax technology hub expansion adding 200 new positions",
            "cloud migration 70% complete across core banking platforms",
        ],
        "ceo_tone": "measured",
        "themes": ["Halifax tech hub", "AI in trading and risk", "cloud migration"],
    },
    ("Q4", 2025): {
        "sentiment": "bullish",
        "revenue": 17.2,
        "net_income": 5.1,
        "cet1": 14.6,
        "roe": 18.2,
        "pcl": 680,
        "highlights": [
            "record fiscal year with earnings growth of 14% year over year",
            "technology transformation delivering $400 million in annual efficiency gains",
            "QTS platform recognized as industry-leading for algorithmic trading",
            "named top employer for technology talent in Canada for second consecutive year",
        ],
        "ceo_tone": "bullish",
        "themes": ["record fiscal year", "QTS platform leadership", "technology talent"],
    },
}


def generate_rbc_transcript(quarter, year):
    """Generate a single RBC earnings call transcript."""
    data = QUARTER_DATA[(quarter, year)]
    turns = []

    # Operator
    turns.append({
        "speaker_name": "Operator",
        "speaker_role": "operator",
        "section_type": "prepared_remarks",
        "content": (
            f"Good morning, and welcome to the Royal Bank of Canada "
            f"{quarter} fiscal year {year} earnings conference call. "
            f"All lines have been placed on mute. After the speakers' remarks, "
            f"there will be a question and answer session. "
            f"I would now like to turn the call over to the head of investor relations."
        ),
    })

    # CEO prepared remarks
    highlights_text = ". ".join(f"We saw {h}" for h in data["highlights"][:2])
    themes_text = " and ".join(data["themes"][:2])

    if data["ceo_tone"] == "bullish":
        opening = f"I am very pleased to report an outstanding {quarter} {year} for Royal Bank of Canada."
        outlook = (
            "Looking ahead, we see significant runway for continued growth. "
            "Our investments in technology, particularly in AI and our Quantitative Technology Services "
            "platform, position us exceptionally well for the future. We are raising our medium-term "
            "targets to reflect this confidence."
        )
    elif data["ceo_tone"] == "confident":
        opening = f"We delivered strong results in {quarter} {year}, demonstrating the power of our diversified business model."
        outlook = (
            "We remain confident in our strategic direction and our ability to deliver consistent, "
            "sustainable growth. Our technology investments are creating durable competitive advantages "
            "that will drive value for shareholders over the long term."
        )
    else:
        opening = f"We delivered solid results in {quarter} {year}, navigating a complex operating environment effectively."
        outlook = (
            "While we remain watchful of macro conditions, our diversified model provides resilience. "
            "We continue to invest in technology and talent to strengthen our competitive position "
            "and are well-prepared for a range of economic scenarios."
        )

    turns.append({
        "speaker_name": RBC["ceo"],
        "speaker_role": "ceo",
        "section_type": "prepared_remarks",
        "content": (
            f"{opening} Total revenue reached ${data['revenue']} billion, "
            f"with net income of ${data['net_income']} billion. Our ROE of {data['roe']}% "
            f"reflects disciplined capital management and strong execution. "
            f"{highlights_text}. Our focus on {themes_text} is delivering measurable results. "
            f"Technology remains a strategic priority. We are investing aggressively in AI, "
            f"machine learning, and cloud infrastructure. Our Quantitative Technology Services "
            f"group continues to expand, and we are seeing real impact from these investments "
            f"in trading efficiency, risk management, and client experience. "
            f"Our Halifax technology hub is a key part of this strategy, bringing together "
            f"top engineering talent to build next-generation platforms. "
            f"{outlook}"
        ),
    })

    # CFO prepared remarks
    turns.append({
        "speaker_name": RBC["cfo"],
        "speaker_role": "cfo",
        "section_type": "prepared_remarks",
        "content": (
            f"Thank you, Dave. Let me walk through the financial details for {quarter} {year}. "
            f"Total revenue was ${data['revenue']} billion, "
            f"{'up' if data['revenue'] > 14.5 else 'consistent with'} from the prior quarter. "
            f"Net income of ${data['net_income']} billion reflects an ROE of {data['roe']}%. "
            f"Our CET1 capital ratio was {data['cet1']}%, well above regulatory minimums "
            f"and providing significant flexibility for organic growth and capital returns. "
            f"Provisions for credit losses were ${data['pcl']} million, "
            f"{'declining' if data['pcl'] < 850 else 'reflecting our prudent approach to'} "
            f"{'as credit quality improves' if data['pcl'] < 850 else 'the current credit environment'}. "
            f"In Capital Markets, revenue {'exceeded expectations' if data['sentiment'] == 'bullish' else 'was solid'}, "
            f"driven by global markets trading and investment banking advisory fees. "
            f"Wealth Management AUM growth was supported by positive net new asset flows "
            f"and market appreciation. Technology spending represented approximately 10% of revenue, "
            f"reflecting our commitment to building scalable, AI-driven platforms."
        ),
    })

    # Q&A section
    analysts_used = random.sample(ANALYSTS, min(3, len(ANALYSTS)))

    for analyst_name, firm in analysts_used:
        topic = random.choice(data["themes"])
        questions = [
            (
                f"Thank you. Dave, can you talk more about the technology investment strategy, "
                f"particularly around {topic}? How should we think about the return on these "
                f"investments over the next two to three years?"
            ),
            (
                f"Good morning. On the {topic} front, can you give us more detail on "
                f"how this is impacting the business operationally? Are you seeing measurable "
                f"efficiency gains from the AI and technology investments?"
            ),
            (
                f"Hi, thanks for taking my question. I wanted to ask about credit quality and "
                f"how you are thinking about provisions going forward given the macro outlook. "
                f"Also any color on the {topic} initiative would be helpful."
            ),
        ]

        turns.append({
            "speaker_name": analyst_name,
            "speaker_role": "analyst",
            "section_type": "qa",
            "content": random.choice(questions),
        })

        # CEO or CFO answer
        if "technology" in topic.lower() or "AI" in topic or "QTS" in topic:
            turns.append({
                "speaker_name": RBC["ceo"],
                "speaker_role": "ceo",
                "section_type": "qa",
                "content": (
                    f"Great question, {analyst_name.split()[0]}. {topic} is central to our strategy. "
                    f"We are building a technology-first bank, and the investments we are making today "
                    f"in AI, cloud, and our QTS platform are creating capabilities that will "
                    f"differentiate us for years to come. Our Halifax technology hub is a great example. "
                    f"We are attracting exceptional engineering talent and they are building systems "
                    f"that improve everything from algorithmic trading to fraud detection to client "
                    f"personalization. The ROI on these investments is accelerating. "
                    f"We are seeing tangible efficiency gains in operations, better risk-adjusted "
                    f"returns in trading, and stronger client engagement through digital channels."
                ),
            })
        else:
            turns.append({
                "speaker_name": RBC["cfo"],
                "speaker_role": "cfo",
                "section_type": "qa",
                "content": (
                    f"Thanks, {analyst_name.split()[0]}. On {topic}, the numbers reflect the "
                    f"underlying strength of our franchise. Our CET1 ratio of {data['cet1']}% "
                    f"gives us significant flexibility. Provisions at ${data['pcl']} million "
                    f"reflect our disciplined approach to risk management. "
                    f"We continue to see strong fundamentals in our Canadian personal banking "
                    f"portfolio and are well-positioned regardless of the rate environment."
                ),
            })

    # Closing
    turns.append({
        "speaker_name": "Operator",
        "speaker_role": "operator",
        "section_type": "qa",
        "content": "This concludes the question and answer session. I will turn the call back to management.",
    })

    turns.append({
        "speaker_name": RBC["ceo"],
        "speaker_role": "ceo",
        "section_type": "qa",
        "content": (
            "Thank you all for joining us today. We are proud of these results and excited "
            "about the opportunities ahead. Our investments in technology and talent are "
            "creating a stronger, more innovative Royal Bank of Canada. "
            "Have a great day."
        ),
    })

    return {
        "company_name": RBC["company_name"],
        "ticker": RBC["ticker"],
        "cik": RBC["cik"],
        "sector": RBC["sector"],
        "exchange": RBC["exchange"],
        "is_sp500": RBC["is_sp500"],
        "quarter": quarter,
        "year": year,
        "turns": turns,
    }


def main():
    output_dir = Path(__file__).resolve().parent.parent / "data" / "sample_transcripts"
    output_dir.mkdir(parents=True, exist_ok=True)

    transcripts = []
    for quarter, year in QUARTERS:
        transcript = generate_rbc_transcript(quarter, year)
        transcripts.append(transcript)

    output_file = output_dir / "ry_transcripts.json"
    with open(output_file, "w") as f:
        json.dump(transcripts, f, indent=2)

    print(f"Generated {len(transcripts)} RBC transcripts")
    print(f"Output: {output_file}")
    print()
    print("To load into the database:")
    print("  curl -X POST http://localhost:8000/api/companies/seed")


if __name__ == "__main__":
    main()
