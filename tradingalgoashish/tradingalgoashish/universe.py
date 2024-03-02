#region imports
from AlgorithmImports import *
from Selection.FundamentalUniverseSelectionModel import FundamentalUniverseSelectionModel
#endregion

class BigTechUniverseSelectionModel(FundamentalUniverseSelectionModel):
    """
    This universe selection model contain the n largest securities in the technology sector.
    """
    
    def __init__(self, universe_settings, universe_size):
        """
        Input:
         - universe_size
            Maximum number of securities in the universe
        """
        super().__init__(None, universe_settings)
        self.universe_size = universe_size
        self.week = -1
        self.hours = None

    def Select(self, algorithm, fundamental):
        if not self.hours or algorithm.LiveMode:
            self.hours = algorithm.MarketHoursDatabase.GetEntry(Market.USA, "SPY", SecurityType.Equity).ExchangeHours
        self.next_open_week = self.hours.GetNextMarketOpen(algorithm.Time, False).isocalendar()[1]

        if self.week == self.next_open_week:
            return Universe.Unchanged
        self.week = self.next_open_week
        
        tech_stocks = [ f for f in fundamental if f.AssetClassification.MorningstarSectorCode == MorningstarSectorCode.Technology ]
        sorted_by_market_cap = sorted(tech_stocks, key=lambda x: x.MarketCap, reverse=True)
        return [ x.Symbol for x in sorted_by_market_cap[:self.universe_size] ]