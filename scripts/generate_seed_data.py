"""
Seed data generator for the Earnings Call Analyzer.

Generates realistic sample earnings call transcripts for S&P 500
companies. The content is structured to be realistic enough to
demonstrate the full feature set: speaker-turn chunking, temporal
comparison, cross-company analysis, and sentiment detection.

Usage:
    python scripts/generate_seed_data.py

This creates JSON files in data/sample_transcripts/ that the
ingestion pipeline can load directly.
"""

import json
import random
import sys
from pathlib import Path

# Companies with realistic metadata
COMPANIES = [
    {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "cik": "0000320193",
        "sector": "Technology",
        "exchange": "NASDAQ",
        "is_sp500": True,
        "ceo": "Tim Cook",
        "cfo": "Luca Maestri",
        "topics": {
            "products": ["iPhone", "Mac", "iPad", "Apple Watch", "Vision Pro"],
            "services": ["App Store", "Apple Music", "iCloud", "Apple TV+", "Apple Pay"],
            "metrics": ["services revenue", "installed base", "gross margin", "R&D spending"],
            "themes": ["AI integration", "privacy", "sustainability", "silicon transition"],
        },
    },
    {
        "ticker": "MSFT",
        "company_name": "Microsoft Corp.",
        "cik": "0000789019",
        "sector": "Technology",
        "exchange": "NASDAQ",
        "is_sp500": True,
        "ceo": "Satya Nadella",
        "cfo": "Amy Hood",
        "topics": {
            "products": ["Azure", "Microsoft 365", "Dynamics", "LinkedIn", "GitHub Copilot"],
            "services": ["Azure AI", "cloud infrastructure", "enterprise solutions"],
            "metrics": ["cloud revenue", "Azure growth rate", "operating margin", "commercial bookings"],
            "themes": ["AI platform", "Copilot adoption", "enterprise transformation", "capital expenditure"],
        },
    },
    {
        "ticker": "GOOGL",
        "company_name": "Alphabet Inc.",
        "cik": "0001652044",
        "sector": "Technology",
        "exchange": "NASDAQ",
        "is_sp500": True,
        "ceo": "Sundar Pichai",
        "cfo": "Ruth Porat",
        "topics": {
            "products": ["Google Search", "YouTube", "Google Cloud", "Pixel", "Waymo"],
            "services": ["advertising", "cloud platform", "AI infrastructure"],
            "metrics": ["search revenue", "cloud revenue", "YouTube ad revenue", "TAC rate"],
            "themes": ["Gemini AI", "search innovation", "cloud profitability", "cost efficiency"],
        },
    },
    {
        "ticker": "AMZN",
        "company_name": "Amazon.com Inc.",
        "cik": "0001018724",
        "sector": "Technology",
        "exchange": "NASDAQ",
        "is_sp500": True,
        "ceo": "Andy Jassy",
        "cfo": "Brian Olsavsky",
        "topics": {
            "products": ["AWS", "Prime", "Alexa", "Kindle", "Ring"],
            "services": ["cloud computing", "e-commerce", "advertising", "logistics"],
            "metrics": ["AWS revenue", "operating income", "free cash flow", "Prime membership"],
            "themes": ["AI services", "fulfillment efficiency", "advertising growth", "cost optimization"],
        },
    },
    {
        "ticker": "JPM",
        "company_name": "JPMorgan Chase & Co.",
        "cik": "0000019617",
        "sector": "Finance",
        "exchange": "NYSE",
        "is_sp500": True,
        "ceo": "Jamie Dimon",
        "cfo": "Jeremy Barnum",
        "topics": {
            "products": ["investment banking", "commercial banking", "asset management", "Chase consumer"],
            "services": ["wealth management", "payments", "lending", "trading"],
            "metrics": ["net interest income", "CET1 ratio", "ROE", "credit loss provisions"],
            "themes": ["interest rate environment", "credit quality", "digital banking", "regulatory capital"],
        },
    },
    {
        "ticker": "NVDA",
        "company_name": "NVIDIA Corp.",
        "cik": "0001045810",
        "sector": "Technology",
        "exchange": "NASDAQ",
        "is_sp500": True,
        "ceo": "Jensen Huang",
        "cfo": "Colette Kress",
        "topics": {
            "products": ["H100", "A100", "Grace Hopper", "DGX", "GeForce RTX"],
            "services": ["data center GPU", "AI training", "inference", "automotive"],
            "metrics": ["data center revenue", "gross margin", "backlog", "gaming revenue"],
            "themes": ["AI demand", "supply constraints", "sovereign AI", "inference scaling"],
        },
    },
    {
        "ticker": "ORCL",
        "company_name": "Oracle Corp.",
        "cik": "0001341439",
        "sector": "Technology",
        "exchange": "NYSE",
        "is_sp500": True,
        "ceo": "Safra Catz",
        "cfo": "Safra Catz",
        "topics": {
            "products": ["Oracle Cloud Infrastructure", "Autonomous Database", "Fusion", "NetSuite"],
            "services": ["cloud applications", "database services", "enterprise solutions"],
            "metrics": ["cloud revenue", "remaining performance obligations", "operating margin"],
            "themes": ["OCI growth", "multi-cloud strategy", "AI integration", "database modernization"],
        },
    },
    {
        "ticker": "UNH",
        "company_name": "UnitedHealth Group Inc.",
        "cik": "0000731766",
        "sector": "Healthcare",
        "exchange": "NYSE",
        "is_sp500": True,
        "ceo": "Andrew Witty",
        "cfo": "John Rex",
        "topics": {
            "products": ["UnitedHealthcare", "Optum Health", "Optum Rx", "Optum Insight"],
            "services": ["health insurance", "pharmacy benefits", "care delivery", "data analytics"],
            "metrics": ["medical care ratio", "revenue per member", "enrollment growth", "operating margin"],
            "themes": ["value-based care", "digital health", "cost management", "membership growth"],
        },
    },
    {
        "ticker": "XOM",
        "company_name": "ExxonMobil Corp.",
        "cik": "0000034088",
        "sector": "Energy",
        "exchange": "NYSE",
        "is_sp500": True,
        "ceo": "Darren Woods",
        "cfo": "Kathryn Mikells",
        "topics": {
            "products": ["upstream production", "downstream refining", "chemical products", "LNG"],
            "services": ["exploration", "refining", "petrochemicals", "carbon capture"],
            "metrics": ["production volume", "refining margins", "capital expenditure", "free cash flow"],
            "themes": ["energy transition", "Permian Basin", "low carbon solutions", "cost discipline"],
        },
    },
    {
        "ticker": "ACN",
        "company_name": "Accenture plc",
        "cik": "0001281761",
        "sector": "Technology",
        "exchange": "NYSE",
        "is_sp500": True,
        "ceo": "Julie Sweet",
        "cfo": "Angie Park",
        "topics": {
            "products": ["consulting", "managed services", "Accenture Cloud First", "Accenture Song"],
            "services": ["digital transformation", "cloud migration", "AI advisory", "cybersecurity"],
            "metrics": ["new bookings", "revenue growth", "operating margin", "headcount"],
            "themes": ["generative AI adoption", "large deal momentum", "talent strategy", "digital transformation"],
        },
    },
    {
        "ticker": "META",
        "company_name": "Meta Platforms Inc.",
        "cik": "0001326801",
        "sector": "Technology",
        "exchange": "NASDAQ",
        "is_sp500": True,
        "ceo": "Mark Zuckerberg",
        "cfo": "Susan Li",
        "topics": {
            "products": ["Facebook", "Instagram", "WhatsApp", "Threads", "Ray-Ban Meta"],
            "services": ["advertising", "Reels", "business messaging", "Reality Labs"],
            "metrics": ["ad revenue", "daily active users", "ad impressions", "Reality Labs losses"],
            "themes": ["AI-driven content", "Reels monetization", "metaverse investment", "efficiency year"],
        },
    },
    {
        "ticker": "TSLA",
        "company_name": "Tesla Inc.",
        "cik": "0001318605",
        "sector": "Automotive",
        "exchange": "NASDAQ",
        "is_sp500": True,
        "ceo": "Elon Musk",
        "cfo": "Vaibhav Taneja",
        "topics": {
            "products": ["Model Y", "Model 3", "Cybertruck", "Semi", "Megapack"],
            "services": ["FSD", "Supercharger network", "energy storage", "insurance"],
            "metrics": ["deliveries", "automotive gross margin", "energy revenue", "free cash flow"],
            "themes": ["FSD progress", "manufacturing efficiency", "energy business growth", "cost reduction"],
        },
    },
    {
        "ticker": "GS",
        "company_name": "Goldman Sachs Group Inc.",
        "cik": "0000886982",
        "sector": "Finance",
        "exchange": "NYSE",
        "is_sp500": True,
        "ceo": "David Solomon",
        "cfo": "Denis Coleman",
        "topics": {
            "products": ["investment banking", "FICC trading", "equities", "asset management"],
            "services": ["M&A advisory", "underwriting", "wealth management", "transaction banking"],
            "metrics": ["net revenue", "ROE", "efficiency ratio", "AUS"],
            "themes": ["capital markets recovery", "strategic refocus", "platform solutions", "expense discipline"],
        },
    },
    {
        "ticker": "V",
        "company_name": "Visa Inc.",
        "cik": "0001403161",
        "sector": "Finance",
        "exchange": "NYSE",
        "is_sp500": True,
        "ceo": "Ryan McInerney",
        "cfo": "Chris Suh",
        "topics": {
            "products": ["Visa Direct", "Visa B2B Connect", "CyberSource", "Visa Token Service"],
            "services": ["payment processing", "cross-border payments", "value-added services", "new flows"],
            "metrics": ["payments volume", "cross-border volume", "processed transactions", "net revenue"],
            "themes": ["new flows and services", "cross-border recovery", "digital payments", "fintech partnerships"],
        },
    },
    {
        "ticker": "WMT",
        "company_name": "Walmart Inc.",
        "cik": "0000104169",
        "sector": "Retail",
        "exchange": "NYSE",
        "is_sp500": True,
        "ceo": "Doug McMillon",
        "cfo": "John David Rainey",
        "topics": {
            "products": ["Walmart U.S.", "Sam's Club", "Walmart International", "Walmart Connect"],
            "services": ["e-commerce", "grocery delivery", "marketplace", "advertising"],
            "metrics": ["comp sales", "e-commerce growth", "operating income", "inventory levels"],
            "themes": ["omnichannel growth", "advertising business", "supply chain automation", "price leadership"],
        },
    },
    {
        "ticker": "CRM",
        "company_name": "Salesforce Inc.",
        "cik": "0001108524",
        "sector": "Technology",
        "exchange": "NYSE",
        "is_sp500": True,
        "ceo": "Marc Benioff",
        "cfo": "Amy Weaver",
        "topics": {
            "products": ["Sales Cloud", "Service Cloud", "Data Cloud", "Slack", "Tableau"],
            "services": ["CRM platform", "AI analytics", "enterprise integration", "industry solutions"],
            "metrics": ["subscription revenue", "RPO", "operating margin", "free cash flow"],
            "themes": ["Einstein AI", "Data Cloud adoption", "margin expansion", "platform consolidation"],
        },
    },
    {
        "ticker": "IBM",
        "company_name": "International Business Machines Corp.",
        "cik": "0000051143",
        "sector": "Technology",
        "exchange": "NYSE",
        "is_sp500": True,
        "ceo": "Arvind Krishna",
        "cfo": "James Kavanaugh",
        "topics": {
            "products": ["Red Hat", "watsonx", "IBM Cloud", "z16 mainframe"],
            "services": ["hybrid cloud", "consulting", "AI platform", "infrastructure"],
            "metrics": ["software revenue", "consulting revenue", "free cash flow", "Red Hat growth"],
            "themes": ["watsonx AI platform", "hybrid cloud strategy", "consulting signings", "portfolio simplification"],
        },
    },
]

# Quarter sequence for generating temporal data
QUARTERS = [
    ("Q1", 2024), ("Q2", 2024), ("Q3", 2024), ("Q4", 2024),
    ("Q1", 2025), ("Q2", 2025), ("Q3", 2025), ("Q4", 2025),
]

# Analyst names for Q&A sections
ANALYSTS = [
    ("Amit Daryanani", "Evercore ISI"),
    ("Wamsi Mohan", "Bank of America"),
    ("Erik Woodring", "Morgan Stanley"),
    ("Shannon Cross", "Cross Research"),
    ("Toni Sacconaghi", "Bernstein"),
    ("Mark Moerdler", "Bernstein"),
    ("Brent Thill", "Jefferies"),
    ("Karl Keirstead", "UBS"),
    ("Keith Weiss", "Morgan Stanley"),
    ("Brad Zelnick", "Deutsche Bank"),
    ("Kash Rangan", "Goldman Sachs"),
    ("Raimo Lenschow", "Barclays"),
]

# Sentiment progression templates
SENTIMENT_TEMPLATES = {
    "bullish": {
        "openings": [
            "We delivered an outstanding quarter with results exceeding our expectations across every segment.",
            "This was a record-breaking quarter for the company, reflecting the strength of our strategy and execution.",
            "I am extremely pleased with our performance this quarter. The momentum we are seeing is unprecedented.",
        ],
        "metrics": [
            "Revenue grew {pct}% year over year, significantly ahead of consensus estimates.",
            "Our {metric} reached an all-time high of ${amount}, driven by strong demand across all regions.",
            "We saw {pct}% growth in {area}, well above our internal targets.",
        ],
        "outlook": [
            "Looking ahead, we see continued strength in demand and expect to deliver above-trend growth next quarter.",
            "Our pipeline is the strongest it has ever been, and we are raising our full-year guidance accordingly.",
            "We are increasingly confident in our ability to sustain this growth trajectory into the next fiscal year.",
        ],
    },
    "neutral": {
        "openings": [
            "We delivered solid results this quarter, broadly in line with our expectations.",
            "Our performance this quarter reflects steady execution against our strategic priorities.",
            "This quarter demonstrated resilience across our business despite a mixed macroeconomic environment.",
        ],
        "metrics": [
            "Revenue of ${amount} represented a {pct}% increase year over year, consistent with our guidance.",
            "{metric} was largely stable compared to the prior quarter, reflecting balanced supply and demand dynamics.",
            "We achieved {pct}% growth in {area}, which is in the range we expected given current market conditions.",
        ],
        "outlook": [
            "For the upcoming quarter, we expect results roughly in line with seasonal patterns.",
            "We are maintaining our full-year guidance and continue to invest in long-term growth opportunities.",
            "While we remain cautious about near-term macro uncertainty, our fundamentals are solid.",
        ],
    },
    "cautious": {
        "openings": [
            "This was a challenging quarter as we navigated headwinds across several of our markets.",
            "Our results this quarter reflect a more difficult operating environment than we anticipated.",
            "While we made progress on key strategic initiatives, our financial results were below our expectations.",
        ],
        "metrics": [
            "Revenue declined {pct}% year over year to ${amount}, impacted by softening demand in key segments.",
            "{metric} came in below expectations, reflecting ongoing challenges in the current environment.",
            "We saw a {pct}% decline in {area} as customers delayed purchasing decisions amid macro uncertainty.",
        ],
        "outlook": [
            "We are taking a more measured approach to our outlook and adjusting our spending accordingly.",
            "Given the current visibility, we are revising our guidance range to reflect a more conservative scenario.",
            "We expect near-term headwinds to persist but believe our strategic positioning will drive recovery.",
        ],
    },
}


def generate_ceo_remarks(company: dict, quarter: str, year: int, sentiment: str) -> list[dict]:
    """Generate CEO prepared remarks with appropriate sentiment."""
    templates = SENTIMENT_TEMPLATES[sentiment]
    topics = company["topics"]
    product = random.choice(topics["products"])
    service = random.choice(topics.get("services", topics["products"]))
    metric = random.choice(topics["metrics"])
    theme = random.choice(topics["themes"])

    opening = random.choice(templates["openings"])
    metric_line = random.choice(templates["metrics"]).format(
        pct=random.randint(3, 28),
        amount=f"{random.randint(10, 95)}.{random.randint(1, 9)}B",
        metric=metric,
        area=product,
    )
    outlook = random.choice(templates["outlook"])

    content = (
        f"{opening} "
        f"In {quarter} {year}, {metric_line} "
        f"Our {theme} strategy continues to gain traction, with {product} showing "
        f"particularly strong adoption among enterprise customers. "
        f"We are investing significantly in {theme} because we believe this represents "
        f"a generational opportunity. The early results from {service} validate our approach. "
        f"{outlook}"
    )

    return [{
        "speaker_name": company["ceo"],
        "speaker_role": "ceo",
        "section_type": "prepared_remarks",
        "content": content,
    }]


def generate_cfo_remarks(company: dict, quarter: str, year: int, sentiment: str) -> list[dict]:
    """Generate CFO financial review remarks."""
    metrics = company["topics"]["metrics"]
    products = company["topics"]["products"]

    revenue = random.randint(15, 120)
    growth = random.randint(-5, 30) if sentiment != "cautious" else random.randint(-8, 5)
    margin = random.randint(20, 45)

    content = (
        f"Thank you, {company['ceo'].split()[0]}. Let me walk through the financial details. "
        f"Total revenue for {quarter} {year} was ${revenue}.{random.randint(1, 9)} billion, "
        f"representing {'growth' if growth > 0 else 'a decline'} of {abs(growth)}% year over year. "
        f"Our {metrics[0]} reached ${random.randint(5, 50)}.{random.randint(1, 9)} billion, "
        f"{'accelerating' if sentiment == 'bullish' else 'consistent with'} "
        f"{'our expectations' if sentiment != 'bullish' else 'the strong demand trends we have been seeing'}. "
        f"Gross margin {'expanded' if growth > 5 else 'was'} {margin}.{random.randint(1, 9)}%, "
        f"{'benefiting from mix shift and operational efficiencies' if margin > 35 else 'reflecting our continued investment in growth'}. "
        f"Operating expenses were well managed, and we generated "
        f"${random.randint(5, 30)}.{random.randint(1, 9)} billion in free cash flow during the quarter. "
        f"We returned ${random.randint(2, 15)} billion to shareholders through dividends and share repurchases. "
        f"For {products[0]}, we saw {random.randint(5, 25)}% growth, "
        f"driven by {'enterprise adoption' if company['sector'] == 'Technology' else 'strong demand fundamentals'}."
    )

    return [{
        "speaker_name": company["cfo"],
        "speaker_role": "cfo",
        "section_type": "prepared_remarks",
        "content": content,
    }]


def generate_qa_section(company: dict, quarter: str, year: int, sentiment: str) -> list[dict]:
    """Generate a Q&A section with analyst questions and executive answers."""
    turns = []
    num_questions = random.randint(3, 5)
    analysts_used = random.sample(ANALYSTS, min(num_questions, len(ANALYSTS)))
    topics = company["topics"]

    for analyst_name, firm in analysts_used:
        product = random.choice(topics["products"])
        metric = random.choice(topics["metrics"])
        theme = random.choice(topics["themes"])

        question_templates = [
            f"Thank you for taking my question. Can you provide more color on the {metric} trajectory? Specifically, how should we think about the sustainability of the growth rate you reported this quarter?",
            f"Great, thanks. On {product}, can you talk about what you are seeing in terms of customer adoption and how the competitive landscape is evolving?",
            f"I wanted to ask about {theme}. How much of your capital allocation is going toward this area, and when do you expect it to start contributing meaningfully to the top line?",
            f"Can you help us understand the margin dynamics better? What is driving the {'expansion' if sentiment == 'bullish' else 'pressure'} and how should we model this going forward?",
            f"My question is on the demand environment. Are you seeing any changes in customer behavior or deal cycles compared to last quarter, particularly in {product}?",
        ]

        question = random.choice(question_templates)
        turns.append({
            "speaker_name": analyst_name,
            "speaker_role": "analyst",
            "section_type": "qa",
            "content": question,
        })

        # Executive answer
        answerer = random.choice([company["ceo"], company["cfo"]])
        answerer_role = "ceo" if answerer == company["ceo"] else "cfo"

        if sentiment == "bullish":
            answer_tone = (
                f"we are seeing exceptionally strong demand and our conviction in {theme} "
                f"has only strengthened. The opportunity ahead of us is significant and we are "
                f"investing aggressively to capture it."
            )
        elif sentiment == "neutral":
            answer_tone = (
                f"we are pleased with the progress on {theme} and continue to see steady "
                f"adoption. We are being disciplined in our investments while ensuring we "
                f"capture the right opportunities."
            )
        else:
            answer_tone = (
                f"while the current environment presents challenges, we are taking proactive "
                f"steps to position {product} for recovery. We are focused on operational "
                f"efficiency and protecting our long-term competitive position."
            )

        answer = (
            f"Thanks, {analyst_name.split()[0]}. Great question. On {metric}, {answer_tone} "
            f"We expect {product} to continue to be a meaningful growth driver as we move "
            f"through the rest of the year. Let me hand it to {company['cfo'].split()[0]} "
            f"for the specific numbers." if answerer_role == "ceo" else
            f"Sure, {analyst_name.split()[0]}. The {metric} trend reflects the underlying "
            f"strength in our business model. When you look at the unit economics, "
            f"{'they continue to improve' if sentiment != 'cautious' else 'we are working to stabilize them'} "
            f"and that gives us confidence in the sustainability of these results."
        )

        turns.append({
            "speaker_name": answerer,
            "speaker_role": answerer_role,
            "section_type": "qa",
            "content": answer,
        })

    return turns


def generate_transcript(company: dict, quarter: str, year: int) -> dict:
    """Generate a complete transcript for one company and quarter."""
    # Vary sentiment across quarters to enable temporal comparison
    quarter_num = int(quarter[1])
    year_offset = year - 2024

    # Create a progression pattern
    seed = hash(f"{company['ticker']}{quarter}{year}") % 100
    if seed < 30:
        sentiment = "bullish"
    elif seed < 70:
        sentiment = "neutral"
    else:
        sentiment = "cautious"

    # Build the transcript
    turns = []
    turns.append({
        "speaker_name": "Operator",
        "speaker_role": "operator",
        "section_type": "prepared_remarks",
        "content": (
            f"Good afternoon, and welcome to the {company['company_name']} "
            f"{quarter} fiscal year {year} earnings conference call. "
            f"All lines have been placed on mute to prevent background noise. "
            f"After the speakers' remarks, there will be a question and answer session. "
            f"I would now like to turn the call over to the head of investor relations."
        ),
    })

    turns.extend(generate_ceo_remarks(company, quarter, year, sentiment))
    turns.extend(generate_cfo_remarks(company, quarter, year, sentiment))
    turns.extend(generate_qa_section(company, quarter, year, sentiment))

    turns.append({
        "speaker_name": "Operator",
        "speaker_role": "operator",
        "section_type": "qa",
        "content": (
            "This concludes the question and answer session. "
            "I would like to turn the call back to management for closing remarks."
        ),
    })

    turns.append({
        "speaker_name": company["ceo"],
        "speaker_role": "ceo",
        "section_type": "qa",
        "content": (
            f"Thank you all for joining us today. We are excited about the opportunities "
            f"ahead and look forward to updating you on our progress next quarter. "
            f"Have a great evening."
        ),
    })

    return {
        "company_name": company["company_name"],
        "ticker": company["ticker"],
        "cik": company["cik"],
        "sector": company["sector"],
        "exchange": company["exchange"],
        "is_sp500": company["is_sp500"],
        "quarter": quarter,
        "year": year,
        "turns": turns,
    }


def main() -> None:
    """Generate all sample transcript files."""
    output_dir = Path(__file__).resolve().parent.parent / "data" / "sample_transcripts"
    output_dir.mkdir(parents=True, exist_ok=True)

    total_transcripts = 0

    for company in COMPANIES:
        company_transcripts = []
        for quarter, year in QUARTERS:
            transcript = generate_transcript(company, quarter, year)
            company_transcripts.append(transcript)
            total_transcripts += 1

        # Write one JSON file per company (contains all quarters)
        output_file = output_dir / f"{company['ticker'].lower()}_transcripts.json"
        with open(output_file, "w") as f:
            json.dump(company_transcripts, f, indent=2)

        print(f"Generated {len(company_transcripts)} transcripts for {company['ticker']}")

    print(f"\nTotal: {total_transcripts} transcripts for {len(COMPANIES)} companies")
    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    main()
