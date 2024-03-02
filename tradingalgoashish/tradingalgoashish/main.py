# region imports
from AlgorithmImports import *

from universe import BigTechUniverseSelectionModel
from alpha import GaussianNaiveBayesAlphaModel
# endregion

class GaussianNaiveBayesClassificationAlgorithm(QCAlgorithm):

    undesired_symbols_from_previous_deployment = []
    checked_symbols_from_previous_deployment = False

    def Initialize(self):
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2024, 2, 20)
        self.SetCash(10000)

        self.SetBrokerageModel(BrokerageName.InteractiveBrokersBrokerage, AccountType.Margin)
        self.SetSecurityInitializer(BrokerageModelSecurityInitializer(self.BrokerageModel, FuncSecuritySeeder(self.GetLastKnownPrices)))

        self.UniverseSettings.DataNormalizationMode = DataNormalizationMode.Raw
        self.SetUniverseSelection(BigTechUniverseSelectionModel(self.UniverseSettings, self.GetParameter("universe_size", 10)))
        
        self.SetAlpha(GaussianNaiveBayesAlphaModel())
        
        self.week = -1
        self.SetPortfolioConstruction(InsightWeightingPortfolioConstructionModel(self.rebalance_func))
        
        self.SetRiskManagement(NullRiskManagementModel())

        self.SetExecution(ImmediateExecutionModel())

        self.SetWarmUp(timedelta(31))

    def rebalance_func(self, time):
        week = self.Time.isocalendar()[1]
        if self.week != week and not self.IsWarmingUp and self.CurrentSlice.QuoteBars.Count > 0:
            self.week = week
            return time
        return None
        
    def OnData(self, data):
        # Exit positions that aren't backed by existing insights.
        # If you don't want this behavior, delete this method definition.
        if not self.IsWarmingUp and not self.checked_symbols_from_previous_deployment:
            for security_holding in self.Portfolio.Values:
                if not security_holding.Invested:
                    continue
                symbol = security_holding.Symbol
                if not self.Insights.HasActiveInsights(symbol, self.UtcTime):
                    self.undesired_symbols_from_previous_deployment.append(symbol)
            self.checked_symbols_from_previous_deployment = True
        
        for symbol in self.undesired_symbols_from_previous_deployment[:]:
            if self.IsMarketOpen(symbol):
                self.Liquidate(symbol, tag="Holding from previous deployment that's no longer desired")
                self.undesired_symbols_from_previous_deployment.remove(symbol)