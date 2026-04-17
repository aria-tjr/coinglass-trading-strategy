#!/usr/bin/env python3
"""
Capital Growth Plan for 20%+ Annual Returns.

Implements systematic capital scaling based on TradeFundrr best practices:
- Compound growth strategies (50-75% reinvestment)
- Position scaling with account growth
- Risk management at scale
- Multiple income streams

Target: Scale from current capital to $100K+ for maximum returns.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import json

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from core.logger import get_logger
from infra.exchange_gateway import BybitGateway

logger = get_logger("capital_growth")


class CapitalGrowthManager:
    """
    Manages systematic capital growth for maximum 20%+ returns.
    
    Based on TradeFundrr proven strategies:
    - 50-75% profit reinvestment
    - Position scaling with equity growth
    - Multiple asset diversification
    """
    
    def __init__(self):
        self.exchange = BybitGateway()
        
        # Growth parameters (TradeFundrr recommendations)
        self.reinvestment_rate = 0.65  # 65% reinvestment
        self.withdrawal_rate = 0.35    # 35% withdrawal
        self.target_monthly_return = 0.022  # 2.2% monthly (27% annual)
        
        # Position scaling rules
        self.base_position_size = 0.95  # 95% aggressive allocation
        self.scaling_increment = 0.10   # Add 10% per $5K growth
        self.max_position_size = 0.98   # Maximum 98% allocation
        
        # Capital milestones
        self.milestones = [
            {'target': 5000, 'reward': 'Optimize SOL strategy'},
            {'target': 10000, 'reward': 'Add ETH optimization'},
            {'target': 25000, 'reward': 'Enable 2x leverage'},
            {'target': 50000, 'reward': 'Multi-timeframe trading'},
            {'target': 100000, 'reward': 'Professional trader status'},
            {'target': 250000, 'reward': '3x leverage + advanced strategies'}
        ]
        
        # Performance tracking
        self.initial_balance = 0
        self.current_balance = 0
        self.total_withdrawn = 0
        self.monthly_returns = []
        
    async def initialize(self):
        """Initialize capital tracking."""
        logger.info("💰 INITIALIZING CAPITAL GROWTH MANAGER")
        logger.info("=" * 60)
        logger.info("Target: Systematic scaling to $100K+ for 20%+ returns")
        
        # Get initial balance
        await self.exchange.initialize()
        account_info = await self.exchange.get_account_balance()
        
        if account_info:
            self.initial_balance = account_info.get('total_balance', 0)
            self.current_balance = self.initial_balance
            
            logger.info(f"💰 Starting Capital: ${self.initial_balance:,.2f}")
            logger.info(f"📊 Target Monthly Return: {self.target_monthly_return*100:.1f}%")
            logger.info(f"🔄 Reinvestment Rate: {self.reinvestment_rate*100:.0f}%")
            
            # Show next milestone
            next_milestone = self.get_next_milestone()
            if next_milestone:
                remaining = next_milestone['target'] - self.current_balance
                logger.info(f"🎯 Next Milestone: ${next_milestone['target']:,} (${remaining:,.0f} to go)")
                logger.info(f"🏆 Reward: {next_milestone['reward']}")
        
        logger.info("✅ Capital growth manager initialized")
    
    def get_next_milestone(self):
        """Get the next capital milestone to reach."""
        for milestone in self.milestones:
            if self.current_balance < milestone['target']:
                return milestone
        return None
    
    async def calculate_monthly_performance(self):
        """Calculate and track monthly performance."""
        try:
            # Get current balance
            account_info = await self.exchange.get_account_balance()
            current_balance = account_info.get('total_balance', 0)
            
            # Calculate monthly return
            if len(self.monthly_returns) > 0:
                last_balance = self.monthly_returns[-1]['ending_balance']
            else:
                last_balance = self.initial_balance
            
            monthly_return = (current_balance - last_balance) / last_balance if last_balance > 0 else 0
            
            # Record performance
            performance = {
                'date': datetime.now().strftime('%Y-%m'),
                'starting_balance': last_balance,
                'ending_balance': current_balance,
                'monthly_return': monthly_return,
                'annual_projection': (1 + monthly_return) ** 12 - 1
            }
            
            self.monthly_returns.append(performance)
            self.current_balance = current_balance
            
            logger.info(f"📊 MONTHLY PERFORMANCE:")
            logger.info(f"   Month: {performance['date']}")
            logger.info(f"   Return: {monthly_return*100:.2f}%")
            logger.info(f"   Balance: ${current_balance:,.2f}")
            logger.info(f"   Annual Projection: {performance['annual_projection']*100:.1f}%")
            
            # Check if target met
            if performance['annual_projection'] >= 0.20:
                logger.info("   🎉 ON TRACK FOR 20%+ ANNUAL TARGET!")
            
            return performance
            
        except Exception as e:
            logger.error(f"Performance calculation failed: {e}")
            return None
    
    async def execute_compound_strategy(self, monthly_profit: float):
        """Execute compound growth strategy."""
        try:
            if monthly_profit <= 0:
                logger.info("📉 No profit to compound this month")
                return
            
            # Calculate reinvestment vs withdrawal
            reinvestment_amount = monthly_profit * self.reinvestment_rate
            withdrawal_amount = monthly_profit * self.withdrawal_rate
            
            logger.info(f"💰 COMPOUND STRATEGY EXECUTION:")
            logger.info(f"   Monthly Profit: ${monthly_profit:,.2f}")
            logger.info(f"   Reinvestment: ${reinvestment_amount:,.2f} ({self.reinvestment_rate*100:.0f}%)")
            logger.info(f"   Withdrawal: ${withdrawal_amount:,.2f} ({self.withdrawal_rate*100:.0f}%)")
            
            # Track total withdrawals
            self.total_withdrawn += withdrawal_amount
            
            # Update position sizing for larger account
            new_balance = self.current_balance
            self.update_position_sizing(new_balance)
            
            # Check for milestone achievements
            await self.check_milestones(new_balance)
            
            logger.info(f"   ✅ Compound strategy executed")
            logger.info(f"   💰 Total Withdrawn: ${self.total_withdrawn:,.2f}")
            
        except Exception as e:
            logger.error(f"Compound strategy execution failed: {e}")
    
    def update_position_sizing(self, new_balance: float):
        """Update position sizing based on account growth."""
        try:
            # Calculate growth from initial balance
            growth_factor = new_balance / self.initial_balance if self.initial_balance > 0 else 1
            
            # Scale position size (TradeFundrr methodology)
            # Add 0.1 lot per $5,000 account growth
            growth_increments = int((new_balance - self.initial_balance) / 5000)
            position_adjustment = growth_increments * 0.01  # 1% per increment
            
            new_position_size = min(
                self.base_position_size + position_adjustment,
                self.max_position_size
            )
            
            logger.info(f"📊 POSITION SIZING UPDATE:")
            logger.info(f"   Account Growth: {(growth_factor-1)*100:.1f}%")
            logger.info(f"   New Position Size: {new_position_size*100:.1f}%")
            logger.info(f"   Growth Increments: {growth_increments}")
            
            # Save updated parameters
            self.base_position_size = new_position_size
            
        except Exception as e:
            logger.error(f"Position sizing update failed: {e}")
    
    async def check_milestones(self, current_balance: float):
        """Check and celebrate milestone achievements."""
        try:
            for milestone in self.milestones:
                if (current_balance >= milestone['target'] and 
                    self.current_balance < milestone['target']):
                    
                    logger.info(f"🎉 MILESTONE ACHIEVED!")
                    logger.info(f"   Target: ${milestone['target']:,}")
                    logger.info(f"   Reward: {milestone['reward']}")
                    
                    # Execute milestone rewards
                    await self.execute_milestone_reward(milestone)
                    
        except Exception as e:
            logger.error(f"Milestone checking failed: {e}")
    
    async def execute_milestone_reward(self, milestone):
        """Execute milestone reward strategies."""
        try:
            reward = milestone['reward']
            
            if 'SOL strategy' in reward:
                logger.info("🔧 Activating SOL optimization strategy")
                # Could trigger SOL strategy optimization
                
            elif 'ETH optimization' in reward:
                logger.info("🔧 Activating ETH optimization strategy")
                # Could trigger ETH strategy optimization
                
            elif '2x leverage' in reward:
                logger.info("⚡ Enabling 2x leverage trading")
                # Could enable leverage features
                
            elif 'Multi-timeframe' in reward:
                logger.info("📊 Activating multi-timeframe analysis")
                # Could enable 4h + daily timeframes
                
            elif 'Professional trader' in reward:
                logger.info("🏆 Professional trader status achieved!")
                # Could unlock advanced features
                
            elif '3x leverage' in reward:
                logger.info("🚀 Advanced strategies with 3x leverage")
                # Could enable advanced strategies
                
        except Exception as e:
            logger.error(f"Milestone reward execution failed: {e}")
    
    def generate_growth_report(self):
        """Generate comprehensive growth report."""
        try:
            if not self.monthly_returns:
                logger.info("📊 No performance data available yet")
                return
            
            # Calculate statistics
            returns = [r['monthly_return'] for r in self.monthly_returns]
            avg_monthly = sum(returns) / len(returns) if returns else 0
            annual_projection = (1 + avg_monthly) ** 12 - 1
            
            total_growth = (self.current_balance - self.initial_balance) / self.initial_balance if self.initial_balance > 0 else 0
            
            logger.info(f"\n📈 CAPITAL GROWTH REPORT")
            logger.info("=" * 60)
            logger.info(f"   Initial Capital: ${self.initial_balance:,.2f}")
            logger.info(f"   Current Balance: ${self.current_balance:,.2f}")
            logger.info(f"   Total Growth: {total_growth*100:.1f}%")
            logger.info(f"   Total Withdrawn: ${self.total_withdrawn:,.2f}")
            logger.info(f"   Average Monthly Return: {avg_monthly*100:.2f}%")
            logger.info(f"   Annual Projection: {annual_projection*100:.1f}%")
            
            # Target assessment
            if annual_projection >= 0.20:
                logger.info(f"   🎯 TARGET STATUS: ACHIEVED ({annual_projection*100:.1f}% > 20%)")
            elif annual_projection >= 0.15:
                logger.info(f"   ⚠️  TARGET STATUS: CLOSE ({annual_projection*100:.1f}%)")
            else:
                logger.info(f"   🔧 TARGET STATUS: NEEDS OPTIMIZATION ({annual_projection*100:.1f}%)")
            
            # Next milestone
            next_milestone = self.get_next_milestone()
            if next_milestone:
                remaining = next_milestone['target'] - self.current_balance
                months_to_target = remaining / (self.current_balance * avg_monthly) if avg_monthly > 0 else float('inf')
                
                logger.info(f"\n🎯 NEXT MILESTONE:")
                logger.info(f"   Target: ${next_milestone['target']:,}")
                logger.info(f"   Remaining: ${remaining:,.0f}")
                logger.info(f"   Estimated Time: {months_to_target:.1f} months")
                logger.info(f"   Reward: {next_milestone['reward']}")
            
        except Exception as e:
            logger.error(f"Growth report generation failed: {e}")
    
    async def run_monthly_review(self):
        """Run monthly capital growth review."""
        logger.info("🔍 RUNNING MONTHLY CAPITAL GROWTH REVIEW")
        logger.info("=" * 60)
        
        # Calculate performance
        performance = await self.calculate_monthly_performance()
        
        if performance:
            # Calculate profit
            monthly_profit = performance['ending_balance'] - performance['starting_balance']
            
            # Execute compound strategy
            await self.execute_compound_strategy(monthly_profit)
            
            # Generate report
            self.generate_growth_report()
            
            # Save data
            self.save_performance_data()
        
        logger.info("✅ Monthly review completed")
    
    def save_performance_data(self):
        """Save performance data to file."""
        try:
            data = {
                'initial_balance': self.initial_balance,
                'current_balance': self.current_balance,
                'total_withdrawn': self.total_withdrawn,
                'monthly_returns': self.monthly_returns,
                'position_size': self.base_position_size
            }
            
            with open('capital_growth_data.json', 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info("💾 Performance data saved")
            
        except Exception as e:
            logger.error(f"Data saving failed: {e}")


async def main():
    """Execute capital growth management."""
    
    print("\n💰 CAPITAL GROWTH MANAGEMENT FOR 20%+ RETURNS")
    print("Based on TradeFundrr systematic scaling strategies")
    print("=" * 70)
    
    # Initialize manager
    manager = CapitalGrowthManager()
    await manager.initialize()
    
    # Show growth plan
    print(f"\n📈 GROWTH PLAN:")
    print(f"   Target: Scale to $100K+ for maximum returns")
    print(f"   Method: 65% reinvestment + 35% withdrawal")
    print(f"   Scaling: Increase position size with growth")
    print(f"   Milestones: 6 levels with strategy upgrades")
    
    # Run monthly review
    await manager.run_monthly_review()
    
    print(f"\n🎯 NEXT ACTIONS:")
    print(f"   1. Monitor daily performance vs targets")
    print(f"   2. Execute compound strategy monthly")
    print(f"   3. Scale position sizes with account growth")
    print(f"   4. Unlock new strategies at milestones")
    print(f"   5. Maintain 20%+ annual return target")


if __name__ == "__main__":
    asyncio.run(main()) 