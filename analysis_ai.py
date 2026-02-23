import os
import google.generativeai as genai
import analysis
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_gemini_key():
    return os.getenv("GEMINI_API_KEY")

def generate_game_plan_real(player_id):
    """
    Generate a REAL Game Plan using Google Gemini API.
    """
    api_key = get_gemini_key()
    if not api_key:
        logger.warning("No GEMINI_API_KEY found. Falling back to mock.")
        return analysis.generate_mock_game_plan(player_id)
        
    # Get Data
    stats = analysis.get_player_analysis(player_id)
    if not stats:
        return None
        
    player_name = "Player" # Ideally fetch name or pass it in. 
    # Since stats result from analysis.get_player_analysis contains ID but not name directly (it returns dict), 
    # we might need to fetch name or just use generic.
    # Actually, let's fetch name quickly or update analysis.py to return it.
    # checking analysis.get_player_analysis return... it has 'player_id' but not name.
    # I will do a quick DB lookup here or update analysis.py.
    # For speed, I'll just use "The Player" or fetch quickly.
    
    conn = analysis.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT name, age, utr_singles FROM players WHERE player_id = ?", (player_id,))
    p_row = c.fetchone()
    conn.close()
    
    if p_row:
        player_name = p_row['name']
        age = p_row['age']
        utr = p_row['utr_singles']
        hand = "Unknown"
    else:
        player_name = "Unknown Player"
        age = "??"
        utr = "??"
        hand = "??"

    # Context Construction
    adv = stats.get('advanced_metrics', {})
    clutch = stats.get('clutch_score', 0)
    age_stats = stats.get('age_analysis', {})
    peers = [p['name'] for p in stats.get('similar_players', [])[:3]]
    
    prompt = f"""
    You are an expert tennis coach and scout.
    
    **Target Player Profile:**
    - Name: {player_name}
    - Age: {age}
    - UTR: {utr}
    
    **Metrics:**
    - Recent Form: {stats['form_rating']}/100
    - Clutch Score: {clutch}/100 (Pressure performance)
    - Upset Rate: {adv.get('upset_rate', 0)}%
    - Bounce Back: {adv.get('bounce_back_rate', 'N/A')}%
    - Consistency: {adv.get('matches_per_month', 0)} matches/mo
    - Peer Comparison: Similar level to {', '.join(peers)}.
    
    **Request:**
    Write a concise "Opponent Intel" report for a player facing {player_name}.
    
    Structure:
    ### AI Opponent Intel
    **Mental Profile**: [One phrase, e.g. "Grinder", "Glass Cannon"]
    
    **Recommended Game Plan**:
    - [Tactic 1]
    - [Tactic 2]
    - [Tactic 3]
    
    **Prediction**:
    [One sentence on flow/outcome]
    
    Keep it tactical and actionable. Use the metrics to justify the advice.
    """
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        return {
            "plan_text": response.text,
            "source": "Gemini Pro"
        }
    except Exception as e:
        logger.error(f"Gemini API Error: {e}")
        return {
            "plan_text": f"**AI Unavailable**: Could not generate plan. Error: {str(e)}",
            "source": "Error"
        }

def generate_quarterly_review(player_id):
    """
    Generate a Quarterly Performance Review using Gemini.
    """
    api_key = get_gemini_key()
    if not api_key:
        return {"report_text": "AI Config Missing", "source": "None"}
        
    # Get Quarterly Stats
    # Note: analysis.py has been updated in memory? If running locally yes.
    try:
        progress = analysis.get_quarterly_progress(player_id)
    except AttributeError:
        # Fallback if module not reloaded in dev env
        return {"report_text": "Analysis module outdated. Restart server.", "source": "System"}

    # Get Basic Profile
    conn = analysis.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT name, age FROM players WHERE player_id = ?", (player_id,))
    p_row = c.fetchone()
    conn.close()
    
    name = p_row['name'] if p_row else "Player"
    age = p_row['age'] if p_row else "??"
    
    # Construct Prompt
    utr_trend = "Stable"
    if progress['utr_delta'] > 0.3: utr_trend = "Rapid Improvement"
    elif progress['utr_delta'] < -0.3: utr_trend = "Declining"
    
    prompt = f"""
    You are an elite tennis coach writing a Quarterly Performance Review.
    
    **Player**: {name} (Age: {age})
    **Period**: {progress['period']}
    
    **Metrics**:
    - UTR: {progress['current_utr']} (Prev: {progress['past_utr']}, Delta: {progress['utr_delta']})
    - Win Rate (Last 20): {progress['current_win_rate']}% (Prev: {progress['past_win_rate']}%, Delta: {progress['win_rate_delta']}%)
    - Match Volume: {progress['volume']} matches (Prev Quarter: {progress['volume_prev']})
    
    **Analysis Context**:
    - UTR Trend: {utr_trend}
    - Volume Change: {"Increased" if progress['volume_delta'] > 0 else "Decreased"}
    
    **Request**:
    Write a professional yet encouraging review for the player/parent.
    
    Structure:
    ### 🏆 Executive Summary
    [1-2 sentences summarizing the trajectory. Be direct.]
    
    ### 🟢 Green Flags (Strengths)
    - **[Strength 1]**: [Detail based on positive deltas/high volume/etc.]
    - **[Strength 2]**: [Detail]
    
    ### 🔴 Red Flags (Concerns)
    - **[Concern 1]**: [Detail based on negative deltas or low volume. If all good, warn about complacency.]
    - **[Concern 2]**: [Detail]
    
    ### 🎯 Training Focus
    [One specific recommendation, e.g. "Increase match play" or "Focus on closing sets" depending on stats.]
    """
    
    try:
        genai.configure(api_key=api_key)
        # Use the discoverable model
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        return {
            "report_text": response.text,
            "metrics": progress
        }
    except Exception as e:
        logger.error(f"Quarterly Review Error: {e}")

def simulate_match_ai(p1_id, p2_id):
    """
    Simulate a match between two players using AI.
    """
    api_key = get_gemini_key()
    if not api_key:
        return {"report_text": "AI Config Missing", "source": "None"}
        
    s1 = analysis.get_player_analysis(p1_id)
    if not s1: return None
    s2 = analysis.get_player_analysis(p2_id)
    if not s2: return None
    
    conn = analysis.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT name FROM players WHERE player_id = ?", (str(p1_id),))
    r1 = c.fetchone()
    p1_name = r1['name'] if r1 else "Player A"
    c.execute("SELECT name FROM players WHERE player_id = ?", (str(p2_id),))
    r2 = c.fetchone()
    p2_name = r2['name'] if r2 else "Player B"
    conn.close()

    prompt = f"""
    Act as a Tennis Data Analyst. SIMULATE a match between:
    
    **Player A**: {p1_name}
    - Form: {s1['form_rating']} | Clutch: {s1['clutch_score']}
    - Bounce Back: {s1['advanced_metrics']['bounce_back_rate']}%
    
    **Player B**: {p2_name}
    - Form: {s2['form_rating']} | Clutch: {s2['clutch_score']}
    - Bounce Back: {s2['advanced_metrics']['bounce_back_rate']}%
    
    **Task**:
    1. **Play Style Clash**: Describe how they match up.
    2. **Key Factor**: What decides this?
    3. **The Prediction**: Winner and Score.
    
    Format:
    ### 🎾 Match Preview
    [Narrative]
    
    ### 🔑 The X-Factor
    [Observation]
    
    ### 🔮 Prediction
    **Winner**: [Name]
    **Score**: [Scoreline]
    """
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        response = model.generate_content(prompt)
        return {"report_text": response.text}
    except Exception as e:
        logger.error(f"Sim Error: {e}")
        return {"report_text": f"Simulation failed: {e}"}


def generate_recruiting_email(player_id):
    """
    Generate a College Recruiting Email draft.
    """
    api_key = get_gemini_key()
    if not api_key:
        return {"email_text": "AI Config Missing", "source": "None"}
        
    s = analysis.get_player_analysis(player_id)
    if not s: return None
    
    # Get Name & Country & UTR
    conn = analysis.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT name, country, age, utr_singles FROM players WHERE player_id = ?", (str(player_id),))
    row = c.fetchone()
    conn.close()
    
    if not row: return None
    name = row['name']
    country = row['country']
    age = row['age']
    utr = row['utr_singles'] or 0.0  # Get actual UTR from player record
    
    # Check eligibility (Loose check, UI handles strict check)
    if age and (age < 15 or age > 19):
        return {"email_text": f"Note: This player is {age} years old. Recruiting briefs are optimized for ages 16-18.", "source": "System"}

    prompt = f"""
    Act as a professional sports agent / mentor.
    Draft a cold email for a tennis recruit to send to a US College Head Coach.
    
    **Player Profile**:
    - Name: {name} (Age: {age}, Country: {country})
    - UTR: {utr:.2f}
    - Key Stats: Form Rating {s['form_rating']}/100, Clutch Score {s['clutch_score']}/100
    - Style: High Volume, Consistent ({s['advanced_metrics'].get('matches_per_month', 0):.1f} matches/mo)
    
    **Task**:
    Write a concise, high-impact email.
    
    Structure:
    **Subject Line**: [Catchy, includes UTR & Grad Year]
    
    **Body**:
    - Introduction (Name, Country)
    - The "Hook": Highlight the UTR and Clutch Score.
    - Recent Form: Mention the volume of play and dedication.
    - Call to Action: "Check my profile / Watch my video".
    
    Tone: Respectful, ambitious, but humble.
    """
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        response = model.generate_content(prompt)
        return {"email_text": response.text}
    except Exception as e:
        logger.error(f"Recruiting Error: {e}")
        return {"email_text": f"Error generating email: {e}"}


def generate_training_focus(player_id, user_context=""):
    """
    Generate personalized training focus recommendations based on weaknesses.
    """
    api_key = get_gemini_key()
    if not api_key:
        return {"recommendations": "AI Config Missing", "source": "None"}
        
    s = analysis.get_player_analysis(player_id)
    if not s: return None
    
    # Get Player Info
    conn = analysis.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT name, utr_singles, tiebreak_wins, tiebreak_losses, three_set_wins, three_set_losses FROM players WHERE player_id = ?", (str(player_id),))
    row = c.fetchone()
    conn.close()
    
    if not row: return None
    
    name = row['name']
    utr = row['utr_singles'] or 0.0
    
    # Calculate weak areas
    tb_wins = row['tiebreak_wins'] or 0
    tb_losses = row['tiebreak_losses'] or 0
    ts_wins = row['three_set_wins'] or 0
    ts_losses = row['three_set_losses'] or 0
    
    tb_total = tb_wins + tb_losses
    tb_pct = (tb_wins / tb_total * 100) if tb_total > 0 else 50
    
    ts_total = ts_wins + ts_losses
    ts_pct = (ts_wins / ts_total * 100) if ts_total > 0 else 50
    
    clutch = s.get('clutch_score', 50)
    form = s.get('form_rating', 50)
    bounce_back = s.get('advanced_metrics', {}).get('bounce_back_rate', 50)
    upset_rate = s.get('advanced_metrics', {}).get('upset_rate', 0)
    
    # Identify weaknesses
    weaknesses = []
    if tb_pct < 45:
        weaknesses.append(f"Tiebreak Win Rate is LOW ({tb_pct:.0f}%). Struggles under scoreboard pressure.")
    if ts_pct < 45:
        weaknesses.append(f"3-Set Win Rate is LOW ({ts_pct:.0f}%). Needs better conditioning or mental stamina in long matches.")
    if clutch and clutch < 45:
        weaknesses.append(f"Clutch Score is POOR ({clutch}). Underperforms in high-pressure moments.")
    if bounce_back and bounce_back < 40:
        weaknesses.append(f"Bounce Back Rate is WEAK ({bounce_back}%). Struggles to recover after losses.")
    if upset_rate is not None and upset_rate < 20:
        weaknesses.append(f"Upset Rate is LOW ({upset_rate}%). Rarely beats higher-rated opponents.")
    
    # If no major weaknesses, mention strengths to maintain
    if not weaknesses:
        weaknesses.append("No critical weaknesses detected! Focus on maintaining consistency and exploring tactical variety.")

    prompt = f"""
    Act as an elite tennis coach creating a personalized TRAINING PLAN.
    
    **Player**: {name} (UTR: {utr:.2f})
    
    **Current Stats**:
    - Clutch Score: {clutch}/100
    - Tiebreak Win Rate: {tb_pct:.0f}% ({tb_wins}W/{tb_losses}L)
    - 3-Set Win Rate: {ts_pct:.0f}% ({ts_wins}W/{ts_losses}L)
    - Bounce Back After Loss: {bounce_back}%
    - Form Rating: {form}/100
    
    **Identified Weaknesses**:
    {chr(10).join(['- ' + w for w in weaknesses])}
    
    {"**Additional Context from Player/Coach**: " + user_context if user_context else ""}
    
    **Task**:
    Generate a focused training plan to address these weaknesses. Be SPECIFIC.
    {"Consider the additional context provided above when making recommendations." if user_context else ""}
    
    Format:
    ### 🎯 Priority Focus Area
    [The #1 thing to work on based on the data]
    
    ### 💪 Recommended Drills
    - **Drill 1**: [Name] - [Description, e.g. "Play 10-point tiebreakers starting at 5-5 in practice"]
    - **Drill 2**: [Name] - [Description]
    - **Drill 3**: [Name] - [Description]
    
    ### 🧠 Mental Training
    [One specific mental training technique based on their weakness]
    
    ### 📅 Weekly Schedule Suggestion
    [Brief suggestion on how to incorporate this into training, e.g. "2x per week, 20 min sessions"]
    """
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        return {
            "recommendations": response.text,
            "weaknesses": weaknesses,
            "stats": {
                "clutch": clutch,
                "tiebreak_pct": round(tb_pct, 1),
                "three_set_pct": round(ts_pct, 1),
                "bounce_back": bounce_back
            }
        }
    except Exception as e:
        logger.error(f"Training Focus Error: {e}")
        return {"recommendations": f"Error generating plan: {e}", "weaknesses": weaknesses}


def generate_trajectory_prediction(player_id, user_context=""):
    """
    Predict career trajectory based on UTR history and growth rate.
    """
    api_key = get_gemini_key()
    if not api_key:
        return {"prediction": "AI Config Missing", "source": "None"}
    
    # Get Player Info & UTR History
    conn = analysis.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT name, utr_singles, age, country, gender FROM players WHERE player_id = ?", (str(player_id),))
    row = c.fetchone()
    
    if not row:
        conn.close()
        return None
    
    name = row['name']
    current_utr = row['utr_singles'] or 0.0
    age = row['age'] or 16
    country = row['country'] or 'Unknown'
    gender = row['gender'] or 'M'  # Default to Male if not specified
    
    # Get UTR History for growth rate calculation
    c.execute("""
        SELECT rating, date FROM utr_history 
        WHERE player_id = ? 
        ORDER BY date ASC
    """, (str(player_id),))
    history = c.fetchall()
    conn.close()
    
    # Calculate growth rate (UTR per year)
    if len(history) >= 2:
        first = history[0]
        last = history[-1]
        from datetime import datetime
        try:
            d1 = datetime.strptime(first['date'], '%Y-%m-%d')
            d2 = datetime.strptime(last['date'], '%Y-%m-%d')
            days_diff = (d2 - d1).days
            if days_diff > 30:  # At least 30 days of data
                years_diff = days_diff / 365.0
                utr_change = last['rating'] - first['rating']
                growth_rate = utr_change / years_diff if years_diff > 0 else 0
            else:
                growth_rate = 0.3  # Default assumption
        except:
            growth_rate = 0.3
    else:
        growth_rate = 0.3  # Default assumption: 0.3 UTR/year growth
    
    # Calculate projections
    projections = {}
    for target_age in [16, 17, 18, 21]:
        if target_age > age:
            years_to_target = target_age - age
            projected_utr = current_utr + (growth_rate * years_to_target)
            projections[target_age] = round(projected_utr, 2)
        elif target_age == age:
            projections[target_age] = current_utr
    
    # Gender-specific College benchmarks (approximate)
    if gender and gender.upper() == 'F':
        # Women's benchmarks are lower
        benchmarks = {
            "D1_Top": 11.5,
            "D1_Mid": 10.0,
            "D2": 8.5,
            "D3": 7.0,
            "NAIA": 6.0
        }
        gender_label = "Women's"
    else:
        # Men's benchmarks
        benchmarks = {
            "D1_Top": 13.0,
            "D1_Mid": 11.5,
            "D2": 10.0,
            "D3": 8.5,
            "NAIA": 7.5
        }
        gender_label = "Men's"
    
    # Pro benchmarks (gender-specific)
    if gender and gender.upper() == 'F':
        pro_benchmarks = {
            "WTA_Top100": 12.5,
            "WTA_Tour": 11.5,
            "ITF_Pro": 10.5
        }
    else:
        pro_benchmarks = {
            "ATP_Top100": 15.0,
            "ATP_Challenger": 13.5,
            "ITF_Pro": 12.0
        }
    
    # Determine trajectory status (College)
    projected_18 = projections.get(18, current_utr)
    if projected_18 >= benchmarks["D1_Top"]:
        status = "🌟 Elite D1 Track"
        status_color = "emerald"
    elif projected_18 >= benchmarks["D1_Mid"]:
        status = "✅ D1 Competitive"
        status_color = "green"
    elif projected_18 >= benchmarks["D2"]:
        status = "📈 D2 Strong"
        status_color = "yellow"
    elif projected_18 >= benchmarks["D3"]:
        status = "🎯 D3 Target"
        status_color = "orange"
    else:
        status = "🔧 Building Foundation"
        status_color = "slate"
    
    # Pro Track Assessment
    pro_track = None
    pro_track_color = None
    if gender and gender.upper() == 'F':
        if projected_18 >= pro_benchmarks["WTA_Top100"]:
            pro_track = "🏆 WTA Top 100 Potential"
            pro_track_color = "violet"
        elif projected_18 >= pro_benchmarks["WTA_Tour"]:
            pro_track = "⚡ WTA Tour Candidate"
            pro_track_color = "purple"
        elif projected_18 >= pro_benchmarks["ITF_Pro"]:
            pro_track = "🎾 ITF Pro Circuit Ready"
            pro_track_color = "indigo"
    else:
        if projected_18 >= pro_benchmarks["ATP_Top100"]:
            pro_track = "🏆 ATP Top 100 Potential"
            pro_track_color = "violet"
        elif projected_18 >= pro_benchmarks["ATP_Challenger"]:
            pro_track = "⚡ ATP Challenger Candidate"
            pro_track_color = "purple"
        elif projected_18 >= pro_benchmarks["ITF_Pro"]:
            pro_track = "🎾 ITF Pro Circuit Ready"
            pro_track_color = "indigo"

    prompt = f"""
    Act as a career counselor for a junior tennis player. Analyze their trajectory.
    
    **Player**: {name} (Age: {age}, Gender: {"Female" if gender and gender.upper() == 'F' else "Male"}, Country: {country})
    **Current UTR**: {current_utr:.2f}
    **Growth Rate**: {growth_rate:.2f} UTR per year
    
    **Projections**:
    {chr(10).join([f"- Age {k}: UTR {v}" for k, v in projections.items()])}
    
    **Benchmarks for {gender_label} US College Tennis (Approximate)**:
    - Top D1 Programs: UTR {benchmarks['D1_Top']}+
    - Mid-Major D1: UTR {benchmarks['D1_Mid']}+
    - D2 Competitive: UTR {benchmarks['D2']}+
    - D3 Strong: UTR {benchmarks['D3']}+
    
    **Trajectory Status**: {status}
    {"**Pro Track Assessment**: " + pro_track if pro_track else "**Pro Track**: Not yet on pro trajectory (focus on college path)"}
    
    {"**Additional Context from Player/Coach**: " + user_context if user_context else ""}
    
    **Task**:
    Write a brief, motivational analysis of their career trajectory. Be realistic but encouraging.
    {"If they show pro potential, discuss whether skipping college might be viable, or if college + pro is a better path." if pro_track else ""}
    {"Consider the additional context provided above in your analysis." if user_context else ""}
    
    Format:
    ### 📈 Trajectory Analysis
    [2-3 sentences summarizing where they are and where they're headed]
    
    ### 🎯 Key Milestone
    [One specific, achievable milestone to target in the next 12 months]
    
    ### 💡 Acceleration Tips
    [2 specific suggestions to accelerate their growth rate]
    
    {"### 🏆 Pro Path Analysis" if pro_track else ""}
    {"[Discuss whether college or going pro directly makes more sense. Consider factors like financial stability, development, and competition level.]" if pro_track else ""}
    
    ### ⚡ Pro Comparison
    [Compare to a pro player's trajectory at the same age, if applicable, or mention realistic expectations]
    """
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        return {
            "analysis": response.text,
            "stats": {
                "current_utr": round(current_utr, 2),
                "age": age,
                "gender": gender_label,
                "growth_rate": round(growth_rate, 2),
                "projections": projections,
                "status": status,
                "status_color": status_color,
                "pro_track": pro_track,
                "pro_track_color": pro_track_color
            },
            "benchmarks": benchmarks,
            "pro_benchmarks": pro_benchmarks
        }
    except Exception as e:
        logger.error(f"Trajectory Error: {e}")
        return {
            "analysis": f"Error generating analysis: {e}",
            "stats": {
                "current_utr": round(current_utr, 2),
                "age": age,
                "gender": gender_label,
                "growth_rate": round(growth_rate, 2),
                "projections": projections,
                "status": status,
                "status_color": status_color,
                "pro_track": pro_track,
                "pro_track_color": pro_track_color
            },
            "benchmarks": benchmarks,
            "pro_benchmarks": pro_benchmarks
        }


def generate_scholarship_estimate(player_id):
    """
    Estimate potential athletic scholarship value based on UTR and gender.
    """
    api_key = get_gemini_key()
    if not api_key:
        return {"estimate": "AI Config Missing", "source": "None"}
    
    # Get Player Info
    conn = analysis.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT name, utr_singles, age, country, gender FROM players WHERE player_id = ?", (str(player_id),))
    row = c.fetchone()
    
    if not row:
        conn.close()
        return None
    
    name = row['name']
    current_utr = row['utr_singles'] or 0.0
    age = row['age'] or 16
    country = row['country'] or 'Unknown'
    gender = row['gender'] or 'M'
    is_international = country.upper() not in ['USA', 'UNITED STATES', 'US', 'AMERICA']
    
    # For younger players, calculate projected UTR at recruiting age
    # Girls: project to age 17, Boys: project to age 17
    recruiting_age = 17
    utr_for_calculation = current_utr
    projected_note = None
    growth_rate = 0.3  # Default
    
    if age and age < recruiting_age:
        # Get UTR History for growth rate calculation
        c2 = conn.cursor()
        c2.execute("""
            SELECT rating, date FROM utr_history 
            WHERE player_id = ? 
            ORDER BY date ASC
        """, (str(player_id),))
        history = c2.fetchall()
        
        # Calculate growth rate
        if len(history) >= 2:
            first = history[0]
            last = history[-1]
            from datetime import datetime
            try:
                d1 = datetime.strptime(first['date'], '%Y-%m-%d')
                d2 = datetime.strptime(last['date'], '%Y-%m-%d')
                days_diff = (d2 - d1).days
                if days_diff > 30:
                    years_diff = days_diff / 365.0
                    utr_change = last['rating'] - first['rating']
                    growth_rate = utr_change / years_diff if years_diff > 0 else 0.3
            except:
                pass
        
        # Project UTR to recruiting age
        years_to_recruiting = recruiting_age - age
        projected_utr = current_utr + (growth_rate * years_to_recruiting)
        utr_for_calculation = round(projected_utr, 2)
        projected_note = f"Based on projected UTR {utr_for_calculation} at age {recruiting_age} (growth rate: +{growth_rate:.2f}/yr)"
    
    conn.close()
    
    # Gender-specific benchmarks and scholarship info
    # Women's D1 Tennis: Full scholarships (8 per team), fully funded
    # Men's D1 Tennis: Equivalency sport (4.5 scholarships split among ~10 players)
    
    if gender and gender.upper() == 'F':
        gender_label = "Women's"
        # Women's benchmarks
        benchmarks = {
            "D1_Top": {"utr": 11.5, "scholarship_pct": (80, 100), "avg_value": 55000},
            "D1_Mid": {"utr": 10.0, "scholarship_pct": (50, 80), "avg_value": 45000},
            "D2": {"utr": 8.5, "scholarship_pct": (40, 70), "avg_value": 20000},
            "D3": {"utr": 7.0, "scholarship_pct": (0, 0), "avg_value": 0},  # D3 no athletic scholarships
            "NAIA": {"utr": 6.0, "scholarship_pct": (30, 60), "avg_value": 15000}
        }
        max_scholarships = "8 full scholarships"
        scholarship_type = "Head-count (Full Ride possible)"
    else:
        gender_label = "Men's"
        # Men's benchmarks (higher UTR requirements, less scholarship money)
        benchmarks = {
            "D1_Top": {"utr": 13.0, "scholarship_pct": (60, 100), "avg_value": 40000},
            "D1_Mid": {"utr": 11.5, "scholarship_pct": (30, 60), "avg_value": 25000},
            "D2": {"utr": 10.0, "scholarship_pct": (25, 50), "avg_value": 15000},
            "D3": {"utr": 8.5, "scholarship_pct": (0, 0), "avg_value": 0},
            "NAIA": {"utr": 7.5, "scholarship_pct": (20, 50), "avg_value": 12000}
        }
        max_scholarships = "4.5 equivalency scholarships"
        scholarship_type = "Equivalency (Partial scholarships)"
    
    # Calculate scholarship estimates for each division
    estimates = {}
    best_fit = None
    best_fit_value = 0
    
    for division, data in benchmarks.items():
        if utr_for_calculation >= data["utr"]:
            # Calculate how far above the minimum they are
            utr_surplus = utr_for_calculation - data["utr"]
            
            # Higher UTR = higher end of scholarship range
            pct_range = data["scholarship_pct"]
            base_pct = pct_range[0]
            max_pct = pct_range[1]
            
            # Each 0.5 UTR above minimum adds ~10% to scholarship
            bonus_pct = min(max_pct - base_pct, utr_surplus * 20)
            estimated_pct = min(max_pct, base_pct + bonus_pct)
            
            # Calculate dollar value
            avg_tuition = {
                "D1_Top": 60000,
                "D1_Mid": 50000,
                "D2": 35000,
                "D3": 55000,  # D3 often private schools with high tuition
                "NAIA": 30000
            }
            
            estimated_value = int((estimated_pct / 100) * avg_tuition[division])
            
            estimates[division] = {
                "eligible": True,
                "scholarship_pct": (int(base_pct), int(min(100, estimated_pct + 10))),
                "estimated_value": estimated_value,
                "utr_threshold": data["utr"],
                "utr_surplus": round(utr_surplus, 2)
            }
            
            # Track best fit
            if estimated_value > best_fit_value:
                best_fit = division
                best_fit_value = estimated_value
        else:
            # Not eligible for this division
            utr_needed = data["utr"] - current_utr
            estimates[division] = {
                "eligible": False,
                "utr_needed": round(utr_needed, 2),
                "utr_threshold": data["utr"]
            }
    
    # Calculate 4-year total
    four_year_total = best_fit_value * 4 if best_fit_value else 0
    
    # International student considerations
    international_note = ""
    if is_international:
        international_note = "As an international student, you may face additional challenges but are highly recruited. Coaches value international experience."
    
    prompt = f"""
    Act as a college tennis recruiting consultant. Provide scholarship guidance.
    
    **Player**: {name} (Age: {age}, Gender: {"Female" if gender and gender.upper() == 'F' else "Male"}, Country: {country})
    **Current UTR**: {current_utr:.2f}
    {"**Projected UTR at " + str(recruiting_age) + "**: " + str(utr_for_calculation) + " (+" + str(round(growth_rate, 2)) + "/yr growth)" if projected_note else ""}
    **UTR Used for Calculation**: {utr_for_calculation}
    **International**: {"Yes" if is_international else "No (USA)"}
    
    **{gender_label} Tennis Scholarship Overview**:
    - Scholarship Type: {scholarship_type}
    - Max Scholarships per Team: {max_scholarships}
    
    **Estimated Scholarship Value by Division**:
    {chr(10).join([f"- {div}: {'Eligible' if est.get('eligible') else 'Need +' + str(est.get('utr_needed', 0)) + ' UTR'} - ${est.get('estimated_value', 0):,}/year" for div, est in estimates.items() if est.get('eligible')])}
    
    **Best Fit Division**: {best_fit or "Building Foundation"}
    **Estimated 4-Year Value**: ${four_year_total:,}
    
    **Task**:
    Provide realistic scholarship guidance. Be encouraging but honest about expectations.
    
    Format:
    ### 💰 Scholarship Summary
    [2-3 sentences on their scholarship potential and best division fit]
    
    ### 🎯 Target Schools
    [Suggest 2-3 types of programs they should target based on their level]
    
    ### 📈 Value Optimization Tips
    [2 specific tips to increase scholarship value - could be UTR improvement or recruiting strategy]
    
    ### ⚠️ Important Considerations
    [Any caveats about the estimates - academic requirements, roster spots, timing, etc.]
    """
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        return {
            "analysis": response.text,
            "estimates": estimates,
            "summary": {
                "current_utr": round(current_utr, 2),
                "utr_for_calculation": utr_for_calculation,
                "age": age,
                "projected_note": projected_note,
                "gender": gender_label,
                "best_fit": best_fit,
                "best_value_per_year": best_fit_value,
                "four_year_total": four_year_total,
                "is_international": is_international,
                "scholarship_type": scholarship_type
            }
        }
    except Exception as e:
        logger.error(f"Scholarship Error: {e}")
        return {
            "analysis": f"Error generating analysis: {e}",
            "estimates": estimates,
            "summary": {
                "current_utr": round(current_utr, 2),
                "utr_for_calculation": utr_for_calculation,
                "age": age,
                "projected_note": projected_note,
                "gender": gender_label,
                "best_fit": best_fit,
                "best_value_per_year": best_fit_value,
                "four_year_total": four_year_total,
                "is_international": is_international,
                "scholarship_type": scholarship_type
            }
        }


def generate_mental_coach(player_id, user_context=""):
    """
    Generate personalized mental game tips and pre-match routine.
    """
    api_key = get_gemini_key()
    if not api_key:
        return {"routine": "AI Config Missing", "source": "None"}
    
    s = analysis.get_player_analysis(player_id)
    if not s: return None
    
    # Get Player Info
    conn = analysis.get_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT name, utr_singles, tiebreak_wins, tiebreak_losses, 
               three_set_wins, three_set_losses, comeback_wins
        FROM players WHERE player_id = ?
    """, (str(player_id),))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return None
    
    name = row['name']
    utr = row['utr_singles'] or 0.0
    
    # Calculate mental game stats
    tb_wins = row['tiebreak_wins'] or 0
    tb_losses = row['tiebreak_losses'] or 0
    ts_wins = row['three_set_wins'] or 0
    ts_losses = row['three_set_losses'] or 0
    comeback_wins = row['comeback_wins'] or 0
    
    tb_total = tb_wins + tb_losses
    tb_pct = (tb_wins / tb_total * 100) if tb_total > 0 else 50
    
    ts_total = ts_wins + ts_losses
    ts_pct = (ts_wins / ts_total * 100) if ts_total > 0 else 50
    
    clutch = s.get('clutch_score', 50)
    form = s.get('form_rating', 50)
    bounce_back = s.get('advanced_metrics', {}).get('bounce_back_rate', 50)
    
    # Identify mental patterns
    mental_patterns = []
    strengths = []
    
    # Analyze patterns
    if tb_pct < 45:
        mental_patterns.append({
            "issue": "Tiebreak Anxiety",
            "detail": f"Wins only {tb_pct:.0f}% of tiebreaks. May tighten up when score is close.",
            "color": "rose"
        })
    elif tb_pct >= 55:
        strengths.append(f"Clutch Performer: {tb_pct:.0f}% tiebreak win rate")
    
    if ts_pct < 45:
        mental_patterns.append({
            "issue": "Late Match Fade",
            "detail": f"Only {ts_pct:.0f}% in 3-setters. May struggle with focus/fitness in long matches.",
            "color": "orange"
        })
    elif ts_pct >= 55:
        strengths.append(f"Marathon Fighter: {ts_pct:.0f}% in 3-set matches")
    
    if clutch and clutch < 45:
        mental_patterns.append({
            "issue": "Pressure Performance",
            "detail": f"Clutch score of {clutch}/100. Underperforms in big moments.",
            "color": "amber"
        })
    elif clutch and clutch >= 60:
        strengths.append(f"Ice in Veins: {clutch}/100 clutch score")
    
    if bounce_back and bounce_back < 40:
        mental_patterns.append({
            "issue": "Recovery Difficulty",
            "detail": f"Only {bounce_back}% bounce back rate after losses.",
            "color": "violet"
        })
    elif bounce_back and bounce_back >= 60:
        strengths.append(f"Resilient: {bounce_back}% bounce back rate")
    
    if comeback_wins >= 5:
        strengths.append(f"Comeback King/Queen: {comeback_wins} comeback victories")
    
    # Determine primary mental focus
    if mental_patterns:
        primary_issue = mental_patterns[0]["issue"]
    else:
        primary_issue = "Maintaining Peak Performance"

    prompt = f"""
    Act as an elite sports psychologist creating a personalized MENTAL GAME PLAN.
    
    **Player**: {name} (UTR: {utr:.2f})
    
    **Mental Performance Stats**:
    - Clutch Score: {clutch}/100
    - Tiebreak Win Rate: {tb_pct:.0f}% ({tb_wins}W/{tb_losses}L)
    - 3-Set Win Rate: {ts_pct:.0f}% ({ts_wins}W/{ts_losses}L)
    - Bounce Back Rate: {bounce_back}%
    - Comeback Wins: {comeback_wins}
    
    **Identified Mental Patterns**:
    {chr(10).join(['- ' + p['issue'] + ': ' + p['detail'] for p in mental_patterns]) if mental_patterns else "- No critical issues detected"}
    
    **Strengths**:
    {chr(10).join(['- ' + st for st in strengths]) if strengths else "- Building mental foundation"}
    
    **Primary Focus Area**: {primary_issue}
    
    {"**Additional Context from Player/Coach**: " + user_context if user_context else ""}
    
    **Task**:
    Create a comprehensive mental game plan. Be SPECIFIC with techniques.
    {"Consider the additional context provided above when creating the mental plan." if user_context else ""}
    
    Format:
    ### 🧠 Mental Profile Summary
    [2-3 sentences describing their mental game tendencies based on the data]
    
    ### ⚡ Pre-Match Routine (15 min before)
    1. [Specific action with timing, e.g. "5 min: Progressive muscle relaxation"]
    2. [Action 2]
    3. [Action 3]
    4. [Action 4 - walk on court visualization]
    
    ### 🎯 In-Match Trigger Phrases
    - [Phrase 1 for specific situation, e.g. "At 30-40: 'One point at a time'"]
    - [Phrase 2]
    - [Phrase 3]
    
    ### 🔄 Reset Routine (Between Points)
    [Specific 10-15 second routine with exact steps]
    
    ### 💪 Pressure Situation Protocols
    - **Serving for the set**: [Specific protocol]
    - **Down break point**: [Specific protocol]
    - **Tiebreak**: [Specific protocol]
    """
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        return {
            "routine": response.text,
            "patterns": mental_patterns,
            "strengths": strengths,
            "stats": {
                "clutch": clutch,
                "tiebreak_pct": round(tb_pct, 1),
                "three_set_pct": round(ts_pct, 1),
                "bounce_back": bounce_back,
                "comeback_wins": comeback_wins,
                "primary_issue": primary_issue
            }
        }
    except Exception as e:
        logger.error(f"Mental Coach Error: {e}")
        return {
            "routine": f"Error generating routine: {e}",
            "patterns": mental_patterns,
            "strengths": strengths,
            "stats": {
                "clutch": clutch,
                "tiebreak_pct": round(tb_pct, 1),
                "three_set_pct": round(ts_pct, 1),
                "bounce_back": bounce_back,
                "comeback_wins": comeback_wins,
                "primary_issue": primary_issue
            }
        }
