def rank_candidates(results: list[dict]) -> list[dict]:
    successful = [r for r in results if r['status']=='success']
    if len({r['scoring_function'] for r in successful})>1: raise ValueError('Cannot rank incompatible scoring functions')
    successful.sort(key=lambda r:(r['best_score_kcal_mol'],r['compound_id']))
    return [{'rank':i, 'compound_id':r['compound_id'], 'best_score_kcal_mol':r['best_score_kcal_mol'],
             'scoring_function':r['scoring_function'], **r['preparation']['descriptors']} for i,r in enumerate(successful,1)]
