from AlgorithmImports import *

from symbol_data import SymbolData

from sklearn.naive_bayes import GaussianNB
from dateutil.relativedelta import relativedelta

class GaussianNaiveBayesAlphaModel(AlphaModel):
    """
    Emits insights in the direction of the prediction made by the SymbolData objects.
    """
    symbol_data_by_symbol = {}
    week = -1

    def Update(self, algorithm, data):
        """
        Called each time the alpha model receives a new data slice.
        
        Input:
         - algorithm
            Algorithm instance running the backtest
         - data
            A data structure for all of an algorithm's data at a single time step
        
        Returns a list of Insights to the portfolio construction model.
        """
        for symbol in set(data.Dividends.Keys) | set(data.Splits.Keys):
            self.symbol_data_by_symbol[symbol].reset()

        # Emit insights once per month
        week = data.Time.isocalendar()[1]
        if self.week == week:
            return []
        
        # Only emit insights when quote data is available, not during corporate actions
        if data.QuoteBars.Count == 0:
            return []
        
        tradable_symbols = {}
        features = [[]]
        for symbol, symbol_data in self.symbol_data_by_symbol.items():
            if data.ContainsKey(symbol) and data[symbol] is not None and symbol_data.IsReady and symbol in self.tradable_symbols:
                tradable_symbols[symbol] = symbol_data
                features[0].extend(symbol_data.features_by_day.iloc[-1].values)
        
        long_symbols = [symbol for symbol, symbol_data in tradable_symbols.items() if symbol_data.model.predict(features) == 1]
        if len(long_symbols) == 0:
            return []
        self.week = week

        insight_expiration_time = list(self.symbol_data_by_symbol.values())[0].hours.GetNextMarketOpen(Expiry.EndOfMonth(algorithm.Time), extendedMarketHours=False) - timedelta(seconds=1)
        weight = 1 / len(long_symbols)
        return [Insight.Price(symbol, insight_expiration_time, InsightDirection.Up, weight=weight) for symbol in long_symbols]
        
        
    def OnSecuritiesChanged(self, algorithm, changes):
        """
        Called each time the universe has changed.
        
        Input:
         - algorithm
            Algorithm instance running the backtest
         - changes
            The additions and removals of the algorithm's security subscriptions
        """
        for security in changes.AddedSecurities:
            self.symbol_data_by_symbol[security.Symbol] = SymbolData(security, algorithm)
            
        for security in changes.RemovedSecurities:
            symbol_data = self.symbol_data_by_symbol.pop(security.Symbol, None)
            if symbol_data:
                symbol_data.dispose()
        
        self.train()
    
    
    def train(self):
        """
        Trains the Gaussian Naive Bayes classifier model.
        """
        features = pd.DataFrame()
        labels_by_symbol = {}

        self.tradable_symbols = []
        for symbol, symbol_data in self.symbol_data_by_symbol.items():
            if symbol_data.IsReady:
                self.tradable_symbols.append(symbol)
                features = pd.concat([features, symbol_data.features_by_day], axis=1)
                labels_by_symbol[symbol] = symbol_data.labels_by_day
        
        # The first and last row can have NaNs because this `train` method fires when 
        #  the universe changes, which is before the consolidated bars close. Let's remove them
        features.dropna(inplace=True) 

        # Find the index which can is common to all of the features and labels
        idx = set([t for t in features.index])
        for i, (symbol, labels) in enumerate(labels_by_symbol.items()):
            a = set([t for t in labels.index])
            idx &= a
        idx = sorted(list(idx))
        
        for symbol, symbol_data in self.symbol_data_by_symbol.items():
            if symbol_data.IsReady:
                symbol_data.model = GaussianNB().fit(features.loc[idx], labels_by_symbol[symbol].loc[idx])