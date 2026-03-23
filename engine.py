import numpy as np
import pandas as pd
import yfinance as yf
import holidays
from datetime import datetime
import calendar

class FinanceEngine:
    def __init__(self):
        # Carrega os feriados nacionais do Brasil para cálculo preciso de dias úteis
        self.br_holidays = holidays.Brazil()

    def calcular_dias_uteis(self, mes, ano):
        """Descobre quantos dias no mês não são fins de semana nem feriados."""
        _, last_day = calendar.monthrange(ano, mes)
        dias = [datetime(ano, mes, d) for d in range(1, last_day + 1)]
        uteis = [d for d in dias if d.weekday() < 5 and d not in self.br_holidays]
        return len(uteis)

    def calcular_irrf_2026(self, bruto):
        """
        Calcula o salário líquido descontando INSS e IRRF (Tabela Progressiva 2026).
        Inclui a isenção de R$ 5.000,00 e o cálculo progressivo do INSS.
        """
        if not bruto or bruto <= 0:
            return 0.0
            
        try:
            # --- CÁLCULO INSS PROGRESSIVO 2026 (Base Salário Mínimo R$ 1.621,00) ---
            if bruto <= 1621.00:
                inss = bruto * 0.075
            elif bruto <= 2902.84:
                inss = (bruto * 0.09) - 24.32
            elif bruto <= 4354.27:
                inss = (bruto * 0.12) - 111.40
            elif bruto <= 8475.55:
                inss = (bruto * 0.14) - 198.49
            else:
                inss = 988.09 # Teto máximo 2026
            
            base_ir = bruto - inss
            
            # --- CÁLCULO IRRF (TABELA + REDUTOR 2026) ---
            if base_ir <= 2259.20: 
                ir_bruto = 0.0
            elif base_ir <= 2826.65: 
                ir_bruto = (base_ir * 0.075) - 169.44
            elif base_ir <= 3751.05: 
                ir_bruto = (base_ir * 0.15) - 381.44
            elif base_ir <= 4664.68: 
                ir_bruto = (base_ir * 0.225) - 662.77
            else: 
                ir_bruto = (base_ir * 0.275) - 896.00

            # Aplicação do Novo Redutor de 2026 (Isenção até R$ 5k)
            if base_ir <= 5000.00:
                ir_final = 0.0
            elif base_ir <= 7350.00:
                redutor = 978.62 - (0.133145 * base_ir)
                ir_final = max(0.0, ir_bruto - redutor)
            else:
                ir_final = ir_bruto 
                
            return float(round(bruto - inss - ir_final, 2))
        except Exception as e:
            print(f"Erro no cálculo de impostos: {e}")
            return float(bruto)

    def monte_carlo_fire(self, inicial, aporte, gasto_futuro, anos, retorno_aa, inflacao_aa, vol_aa):
        meses = anos * 12
        retorno_real_mensal = ((1 + retorno_aa) / (1 + inflacao_aa)) ** (1/12) - 1
        vol_mensal = vol_aa / np.sqrt(12)
        
        resultados = []
        for _ in range(100):
            caminho = [inicial]
            for _ in range(meses):
                ret = np.random.normal(retorno_real_mensal, vol_mensal)
                novo = caminho[-1] * (1 + ret) + aporte - gasto_futuro
                caminho.append(max(novo, 0))
            resultados.append(caminho)
        return resultados

    @staticmethod
    def get_usd():
        try:
            usd = yf.download("USDBRL=X", period="1d", progress=False)
            return float(usd['Close'].iloc[-1])
        except:
            return 5.25

    @staticmethod
    def fetch_prices(tickers):
        if not tickers: return {}
        t_fmt = [t + ".SA" if len(t) <= 6 and "." not in t else t for t in tickers]
        try:
            data = yf.download(t_fmt, period="1d", group_by='ticker', progress=False)
            precos = {}
            for t in tickers:
                raw = t + ".SA" if len(t) <= 6 and "." not in t else t
                if len(tickers) > 1:
                    precos[t] = float(data[raw]['Close'].iloc[-1])
                else:
                    precos[t] = float(data['Close'].iloc[-1])
            return precos
        except:
            return {t: 0.0 for t in tickers}

    def auto_categorizar(self, descricao):
        desc = str(descricao).upper()
        regras = {
            "Alimentação": ["IFOOD", "MERCADO", "PADARIA", "RESTAURANTE", "ZE DELIVERY", "RAPPI", "CARREFOUR", "ASSAI", "ATACADAO"],
            "Transporte": ["UBER", "99", "POSTO", "GASOLINA", "METRO", "IPVA", "SEMPARAR", "LOCALIZA", "CONECTCAR"],
            "Habitação": ["CEMIG", "COPASA", "ENEL", "CONDOMINIO", "ALUGUEL", "INTERNET", "VIVO", "CLARO", "TIM"],
            "Saúde": ["FARMACIA", "UNIMED", "SULAMERICA", "DROGASIL", "RAIA", "PAGUE MENOS"],
            "Lazer": ["NETFLIX", "SPOTIFY", "CINEMA", "STEAM", "INGRESSO", "AMAZON", "PLAYSTATION", "SYMPLA", "BET", "SPORTINGBET"],
            "Educação": ["CURSO", "FACULDADE", "UDEMY", "ALURA", "HOTMART"],
            "Investimentos": ["XP", "CLEAR", "RICO", "NUBANK", "INTER", "BTG", "AVENUE"]
        }
        for cat, palavras in regras.items():
            if any(p in desc for p in palavras):
                natureza = "Essencial" if cat in ["Alimentação", "Habitação", "Saúde", "Transporte"] else "Estilo de Vida"
                if cat == "Investimentos": natureza = "Renda Extra"
                return cat, natureza
        return "Outros", "Estilo de Vida"