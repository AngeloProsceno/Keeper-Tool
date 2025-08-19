import streamlit as st
import requests
import pandas as pd
from collections import defaultdict

st.set_page_config(layout="wide")
st.set_page_config(page_title="SFGL: Keeper-Tool", page_icon="NPC.jpg")

# Add CSS for HTML tables with a modern navy blue and grey color scheme
st.markdown("""
<style>
.dataframe {
    width: 100% !important;
    table-layout: auto !important;
    margin: 0 auto;
    border-collapse: collapse;
}
.dataframe th, .dataframe td {
    text-align: center;
    padding: 10px;
    white-space: pre-wrap;
    word-break: break-word;
    vertical-align: top;
    min-width: 150px;
    border: 1px solid #e0e0e0;
}
.roster-table th, .roster-table td {
    font-size: 12px;
    min-width: 100px;
    padding: 5px;
    border: 1px solid #e0e0e0;
}
.dataframe th {
    background-color: #1a2a44; /* Navy blue header */
    color: #ffffff;
    font-weight: bold;
}
.roster-table th {
    background-color: #1a2a44; /* Navy blue header */
    color: #ffffff;
    font-weight: bold;
}
.dataframe td {
    background-color: #f5f7fa; /* Light grey background */
}
.roster-table td {
    background-color: #f5f7fa; /* Light grey background */
}
.dataframe tr:nth-child(even) td {
    background-color: #e9ecef; /* Slightly darker grey for even rows */
}
.roster-table tr:nth-child(even) td {
    background-color: #e9ecef; /* Slightly darker grey for even rows */
}
div[data-testid="stVerticalBlock"] {
    width: 100%;
    max-width: none !important;
}
.stSelectbox div[role="combobox"] {
    max-width: 150px !important;
}
.stButton>button {
    background-color: #1a2a44;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 5px;
}
.stButton>button:hover {
    background-color: #2c4066; /* Darker navy on hover */
}
</style>
""", unsafe_allow_html=True)

# Hardcoded league IDs for previous seasons
draft_year_to_prev_league_id = {
    2024: '992340899759714304',  # 2023 season for 2024 draft
    2025: '1120508461290291200',  # 2024 season for 2025 draft
}

st.title("Who the FUCK can I keep?")
st.text("if you cant read anything hit the 3 dots in the top right (SETTINGS) & change to 'light mode'")
draft_year = st.selectbox("Draft Year", [2024, 2025], index=1)

if st.button("Show me plz"):
    league_id = draft_year_to_prev_league_id.get(draft_year)
    if not league_id:
        st.error("Invalid Draft Year selected.")
    else:
        prev_year = draft_year - 1
        with st.spinner("Loading data..."):
            # Fetch all NFL players for names
            players_url = "https://api.sleeper.app/v1/players/nfl"
            players_response = requests.get(players_url)
            players = players_response.json() if players_response.status_code == 200 else {}

            # Fetch league details to get draft ID
            league_url = f"https://api.sleeper.app/v1/league/{league_id}"
            league_response = requests.get(league_url)
            league = league_response.json() if league_response.status_code == 200 else {}
            draft_id = league.get('draft_id')

            # Fetch draft picks if draft_id exists
            player_to_draft_round = {}
            player_to_is_keeper = {}
            drafted_players = set()
            draft_picks = []
            if draft_id:
                draft_picks_url = f"https://api.sleeper.app/v1/draft/{draft_id}/picks"
                draft_picks_response = requests.get(draft_picks_url)
                draft_picks = draft_picks_response.json() if draft_picks_response.status_code == 200 else []
                for pick in draft_picks:
                    player_id = pick.get('player_id')
                    if player_id:
                        player_to_draft_round[player_id] = pick['round']
                        player_to_is_keeper[player_id] = pick.get('is_keeper', False)
                        drafted_players.add(player_id)

            # Fetch rosters
            rosters_url = f"https://api.sleeper.app/v1/league/{league_id}/rosters"
            rosters_response = requests.get(rosters_url)
            rosters = rosters_response.json() if rosters_response.status_code == 200 else []

            # Sort rosters by roster_id
            sorted_rosters = sorted(rosters, key=lambda r: r.get('roster_id', 0))

            # Fetch users for team names
            users_url = f"https://api.sleeper.app/v1/league/{league_id}/users"
            users_response = requests.get(users_url)
            users = users_response.json() if users_response.status_code == 200 else []
            owner_to_name = {}
            for user in users:
                owner_id = user.get('user_id')
                name = user.get('display_name', 'Unknown')
                team_name = user.get('metadata', {}).get('team_name', name)
                owner_to_name[owner_id] = team_name

            # Map roster_id to team_name
            roster_id_to_team = {roster['roster_id']: owner_to_name.get(roster['owner_id'], 'Unknown Team') for roster in rosters}

            # Fetch all transactions (loop over weeks until empty)
            transactions = []
            for week in range(1, 25):
                trans_url = f"https://api.sleeper.app/v1/league/{league_id}/transactions/{week}"
                trans_response = requests.get(trans_url)
                if trans_response.status_code != 200:
                    break
                trans = trans_response.json()
                if not trans:
                    break
                transactions.extend(trans)

            # Collect add transactions per roster/player
            add_transactions = defaultdict(lambda: defaultdict(list))
            for trans in transactions:
                if trans.get('status') != 'complete':
                    continue
                adds = trans.get('adds') or {}
                for player_id, roster_id in adds.items():
                    add_transactions[roster_id][player_id].append(trans)

            # Prepare data for keeper board
            team_to_round_players = defaultdict(lambda: defaultdict(list))

            # Prepare data for draft board
            team_to_round_drafted = defaultdict(lambda: defaultdict(list))

            for pick in draft_picks:
                player_id = pick.get('player_id')
                if player_id:
                    roster_id = pick.get('roster_id')
                    if roster_id:
                        team_name = roster_id_to_team.get(roster_id, 'Unknown Team')
                        round_ = pick['round']
                        player_name = f"{players.get(player_id, {}).get('first_name', '')} {players.get(player_id, {}).get('last_name', '')}".strip() or 'Unknown'
                        if pick.get('is_keeper', False):
                            player_name += ' (Kept)'
                        team_to_round_drafted[team_name][round_].append(player_name)

            # Prepare roster data: group by team and position
            team_to_pos_to_players = defaultdict(lambda: defaultdict(list))
            for roster in sorted_rosters:
                roster_id = roster.get('roster_id')
                owner_id = roster.get('owner_id')
                team_name = owner_to_name.get(owner_id, 'Unknown Team')

                players_on_roster = roster.get('players', [])
                for player_id in players_on_roster:
                    player_data = players.get(player_id, {})
                    player_name = f"{player_data.get('first_name', '')} {player_data.get('last_name', '')}".strip() or 'Unknown'
                    position = player_data.get('position', 'Unknown')
                    add_trans_list = add_transactions[roster_id][player_id]
                    if add_trans_list:
                        latest_add = max(add_trans_list, key=lambda t: t['status_updated'])
                        acq_type = latest_add['type']
                        if acq_type == 'waiver':
                            bid = latest_add.get('settings', {}).get('waiver_bid')
                            acq_method = f"Waiver (FAAB ${bid})" if bid is not None else "Waiver"
                        elif acq_type == 'free_agent':
                            acq_method = "Free Agent Pickup"
                        elif acq_type == 'trade':
                            acq_method = "Trade"
                        else:
                            acq_method = acq_type.capitalize()
                    else:
                        if player_id in player_to_draft_round:
                            if player_to_is_keeper.get(player_id, False):
                                acq_method = "Kept"
                            else:
                                acq_method = "Draft"
                        else:
                            acq_method = "Unknown"
                    # Calculate keeper round
                    if player_id in player_to_draft_round:
                        entry_round = player_to_draft_round[player_id]
                        proposed = entry_round - 3
                        if proposed < 1:
                            keeper_round = "Not Eligible"
                        elif not player_to_is_keeper.get(player_id, False) and entry_round <= 3:
                            keeper_round = "Not Eligible (Drafted in Rounds 1-3)"
                        else:
                            keeper_round = proposed
                    else:
                        keeper_round = 10
                    keeper_round_str = str(keeper_round) if isinstance(keeper_round, int) else keeper_round

                    team_to_pos_to_players[team_name][position].append((player_name, acq_method, keeper_round_str))

                    # Add to keeper board if eligible
                    if isinstance(keeper_round, int):
                        team_to_round_players[team_name][keeper_round].append(player_name)

            # Team names
            team_names = [roster_id_to_team.get(r.get('roster_id'), 'Unknown Team') for r in sorted_rosters]

            # Get unique positions in desired order
            all_positions = set()
            for team in team_to_pos_to_players:
                all_positions.update(team_to_pos_to_players[team].keys())
            desired_order = ['QB', 'RB', 'WR', 'TE', 'K', 'DEF']
            positions = [p for p in desired_order if p in all_positions] + [p for p in sorted(all_positions) if p not in desired_order]

            # Split teams into two groups of 5
            mid = len(team_names) // 2 + len(team_names) % 2  # First group gets one more if odd
            team_group1 = team_names[:mid]
            team_group2 = team_names[mid:]

            # Function to build roster df for a group of teams
            def build_roster_df(teams):
                data = []
                for pos in positions:
                    row = [pos]
                    for team in teams:
                        pls = team_to_pos_to_players[team].get(pos, [])
                        pls.sort(key=lambda x: x[0])  # Sort by player name
                        players_str = '\n'.join(p[0] for p in pls) if pls else ''
                        acq_str = '\n'.join(p[1] for p in pls) if pls else ''
                        keeper_str = '\n'.join(p[2] for p in pls) if pls else ''
                        row.extend([players_str, acq_str, keeper_str])
                    data.append(row)

                # Create multi-index columns
                from itertools import chain
                columns_tuples = [(' ', 'Position')] + list(chain.from_iterable(((team, 'Players'), (team, 'Acquisition Method'), (team, 'Keeper Round')) for team in teams))
                multi_columns = pd.MultiIndex.from_tuples(columns_tuples)

                df = pd.DataFrame(data, columns=multi_columns)
                return df

            roster_df1 = build_roster_df(team_group1)
            roster_df2 = build_roster_df(team_group2)

            # Keeper board DataFrame
            keeper_data = []
            for rnd in range(1, 17):
                row = [rnd]
                for team_name in team_names:
                    pls = team_to_round_players[team_name].get(rnd, [])
                    row.append('\n'.join(sorted(pls)) if pls else '')
                keeper_data.append(row)
            keeper_df = pd.DataFrame(keeper_data, columns=['Round'] + team_names)

            # Draft board DataFrame
            draft_data = []
            for rnd in range(1, 17):
                row = [rnd]
                for team_name in team_names:
                    pls = team_to_round_drafted[team_name].get(rnd, [])
                    row.append('\n'.join(sorted(pls)) if pls else '')
                draft_data.append(row)
            draft_df = pd.DataFrame(draft_data, columns=['Round'] + team_names)

            # Process dfs for HTML rendering
            def replace_newline(x):
                if isinstance(x, str):
                    return x.replace('\n', '<br>')
                return x

            roster_df1 = roster_df1.map(replace_newline)
            roster_df2 = roster_df2.map(replace_newline)
            keeper_df = keeper_df.map(replace_newline)
            draft_df = draft_df.map(replace_newline)

        st.success("Here you go you lazy sack of shit")

        tab1, tab2, tab3 = st.tabs(["Draft Keeper Board", f"{prev_year} Draft", f"{prev_year} Rosters"])

        with tab1:
            html = keeper_df.to_html(escape=False, index=False, classes='dataframe')
            st.markdown(f'<div style="width:100%;">{html}</div>', unsafe_allow_html=True)

        with tab2:
            html = draft_df.to_html(escape=False, index=False, classes='dataframe')
            st.markdown(f'<div style="width:100%;">{html}</div>', unsafe_allow_html=True)

        with tab3:
            html1 = roster_df1.to_html(escape=False, index=False, classes=['dataframe', 'roster-table'])
            st.markdown(f'<div style="width:100%;">{html1}</div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)  # Add spacing between blocks
            html2 = roster_df2.to_html(escape=False, index=False, classes=['dataframe', 'roster-table'])
            st.markdown(f'<div style="width:100%;">{html2}</div>', unsafe_allow_html=True)