import argparse
import numpy as np
import pandas as pd

def get_mean_eff( game_map, team_name ):
    # return the mean efficiency for the requested team (AdjOE or AdjDE)
    mean_efficiency = 1.0
    if team_name in game_map:
        eff_map = game_map[ team_name ]
        efficiencies = list( eff_map.values() )
        mean_efficiency = np.mean( efficiencies )

    return mean_efficiency

def calc_game_eff( ppp_game, opp_eff, mean_ppp, site_factor ):
    return calc_game_eff_kenpom( ppp_game, opp_eff, mean_ppp, site_factor )

def calc_game_eff_torvik( ppp_game, opp_eff, mean_ppp, site_factor ):
    game_eff = ppp_game / ( opp_eff * site_factor / mean_ppp )
    return game_eff

def calc_game_eff_kenpom( ppp_game, opp_eff, mean_ppp, site_factor ):
    game_eff = ppp_game - opp_eff * site_factor + mean_ppp
    return game_eff

def add_game_eff( game_map, team_name, date, efficiency ):
    # adds game efficiency to game map:
    # game_map -> [team_name] -> { 'date': 1.332322334,
    #                             'date': 0.83982398 }
    eff_map = { date: efficiency }
    delta = 1
    if team_name in game_map:
        eff_map = game_map[ team_name ]
        if date in eff_map:
            existing_efficiency = eff_map[ date ]
            delta = existing_efficiency - efficiency
        eff_map[ date ] = efficiency
    game_map[ team_name ] = eff_map

    return game_map, delta

def calc_efficiency_margins( ades, aoes ):
    assert set( ades.keys() ) == set( aoes.keys() ), f"AdjDE teams ({len(ades.keys())}) != AdjOE teams ({len(aoes.keys())})"

    ems = {}

    for team, game_dates in aoes.items():
        mean_aoe = np.mean( list( game_dates.values() ) )
        mean_ade = np.mean( list( ades[team].values() ) )
        ems[ team ] = mean_aoe - mean_ade

    return ems

def calc_efficiencies( off_df, def_df, date ):
    # sort by date in ascending order
    off_df = off_df.sort_values( 'date' )
    def_df = def_df.sort_values( 'date' )
    off_df['datetime'] = pd.to_datetime( off_df['date'] )
    def_df['datetime'] = pd.to_datetime( def_df['date'] )

    ades = {}
    aoes = {}
    # offense

    # for each date, grab all of the games
    this_datetime = pd.to_datetime( date )
    off_slice_df = off_df[ (off_df['datetime'] <= this_datetime) ].copy()
    def_slice_df = def_df[ (def_df['datetime'] <= this_datetime) ].copy()

    assert len(off_slice_df.index) == len(def_slice_df.index), f"Number of Offensive stat rows ({len(off_slice_df.index)} != to Number of Defensive stat rows ({len(def_slice_df.index)})"

    # for each game, calculate PPP
    ppps = ( off_slice_df['points_for'] / off_slice_df['poss'] ).values
    mean_ppp = np.mean( ppps )

    # If home game, weight multiplier is 0.986; away game: 1.014; neutral game: 1.0
    off_slice_df['site_factor'] = off_slice_df.apply( lambda row: 1.0 if row['site'] == 'N' else ( 0.986 if row['site'] == 'H' else 1.014 ), axis=1 )

    NOT_CONVERGED = True
    epsilon = 0.01
    while NOT_CONVERGED:
        NOT_CONVERGED = False
        for index, row in off_slice_df.iterrows():
            site_factor = row['site_factor']
            off_ppp = row['points_for'] / row['poss']
            opp_ade = get_mean_eff( ades, row['opponent_name'] )
            # now, calculate game AdjOE
            game_aoe = calc_game_eff( off_ppp, opp_ade, site_factor, mean_ppp )
            aoes, off_delta = add_game_eff( aoes, row['team_name'], row['date'], game_aoe )

            mean_aoe = get_mean_eff( aoes, row['team_name'] )
            # now opp AdjDE
            opp_game_ade = calc_game_eff( off_ppp, mean_aoe, site_factor, mean_ppp )
            ades, def_delta = add_game_eff( ades, row['opponent_name'], row['date'], opp_game_ade )
            if off_delta > epsilon or def_delta > epsilon:
                NOT_CONVERGED = True

    # now calc EM means, sort and print
    efficiency_margins = calc_efficiency_margins( ades, aoes )
    sorted_teams = sorted(efficiency_margins, key=efficiency_margins.get, reverse=True)
    for rank, team in enumerate( sorted_teams ):
        print( f"{rank+1}. {team} {efficiency_margins[team]}" )

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument( "-y", "--year", help="Compiles stats for the specified year", required=True )
    parser.add_argument( "-d", "--date", help="cutoff date (e.g., 2020-03-20", required=True )
    args = parser.parse_args()

    year = None
    if args.date:
        date = args.date
    if args.year:
        year = int( args.year )

    def_stats_df = pd.read_csv( f"offensive_stats_{year}.csv" )
    off_stats_df = pd.read_csv( f"offensive_stats_{year}.csv" )
    calc_efficiencies( off_stats_df, def_stats_df, date )
