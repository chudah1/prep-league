from collections import defaultdict
from dataclasses import dataclass
import heapq
from bisect import bisect_right

@dataclass
class BankEntry:
    account_id: str
    amount: int = 0


@dataclass
class Payment:
    execute_at: float
    payment_counter: int
    account_id: str
    amount: float


class Bank:

    def __init__(self):

        self.bank: dict[str, BankEntry] = {}
        #{account_id-> amount}
        self.transfers: dict[str, int] = defaultdict(int)
        # {payment_id: Payment(id=1, amount=, executed_at)}
        self.scheduled_payments: dict[str, Payment] = {}
        self.payment_counter = 0
        #acct_id -> [(time, balance)]
        self.audit: dict[str, list[tuple]] = defaultdict(list)


    def _execute_scheduled_payments(self, timestamp:int)->None:
        payments = [
        (payment.execute_at, payment.payment_counter, payment.account_id, payment.amount)
        for payment_id, payment in self.scheduled_payments.items()
    ]
        heapq.heapify(payments)

        while payments and payments[0][0] <= timestamp:
            execute_at, payment_counter, account_id, amount = heapq.heappop(payments)
            account = self.bank.get(account_id)
            if (account.amount >= amount):
                account.amount -= amount
                self.transfers[account_id] += amount
                self.audit[account_id].append((execute_at, account.amount))

            payment_id = f"payment{payment_counter}"
            del self.scheduled_payments[payment_id]

            

    def create_account(self, timestamp: int, account_id: str)->bool:
        self._execute_scheduled_payments(timestamp)

        is_created = self.bank.get(account_id)
        if not is_created:
            self.bank[account_id] = BankEntry(account_id)
            self.audit[account_id].append((timestamp, 0))
            return True

        return False

    def deposit(self, timestamp:int, account_id: str, amount: float) -> int | None:
        self._execute_scheduled_payments(timestamp)

        if self.bank.get(account_id) is None:
            return None

        account = self.bank.get(account_id)
        #
        new_balance = amount + account.amount
        account.amount = new_balance        
        self.audit[account_id].append((timestamp, new_balance))

        return new_balance

    def transfer(self, timestamp, source_id, target_id, amount) -> int | None:
        self._execute_scheduled_payments(timestamp)

        if self.bank.get(source_id) is None or self.bank.get(target_id) is None or source_id == target_id:
            return None

        elif self.bank.get(source_id).amount < amount:
            return None
        else:
            source_account = self.bank.get(source_id)
            target_account = self.bank.get(target_id)
            source_account.amount -= amount
            target_account.amount += amount
            source_amount = source_account.amount
            target_amount = target_account.amount

            self.transfers[source_id] += amount
            self.audit[source_id].append((timestamp, source_amount))
            self.audit[target_id].append((timestamp, target_amount))

            return source_amount
        
    def top_spenders(self, timestamp, n) -> list[str]:
        self._execute_scheduled_payments(timestamp)

        spenders = []
        if n <=0: return []


        for acc_id in self.bank:
            total = self.transfers.get(acc_id, 0)
            spenders.append((total, acc_id))

        spenders.sort(key=lambda x: (-x[0], x[1]))

        return [f"{acc_id}({amount})" for amount, acc_id in spenders[:n]]


    def schedule_payment(self, timestamp, account_id, amount, delay) -> str | None:
        self._execute_scheduled_payments(timestamp)

        if self.bank.get(account_id) is None:
            return None

        self.payment_counter += 1
        payment_id = f"payment{self.payment_counter}"
        self.scheduled_payments[payment_id] = Payment(timestamp+delay, self.payment_counter, account_id, amount)

        return payment_id

    def cancel_payment(self, timestamp, account_id, payment_id) -> bool:

        self._execute_scheduled_payments(timestamp)
        if (self.scheduled_payments.get(payment_id)) is None:
            return False

        payment_details = self.scheduled_payments.get(payment_id)
        if account_id != payment_details.account_id:
            return False
        del self.scheduled_payments[payment_id]
        return True

    def merge_accounts(self, timestamp, account_id_1, account_id_2) -> bool:
        self._execute_scheduled_payments(timestamp)

        target = self.bank.get(account_id_1)
        source = self.bank.get(account_id_2)

        if account_id_2 == account_id_1 or target is None or source is None:
            return False
        target.amount += source.amount

        self.transfers[account_id_1] += self.transfers[account_id_2]

        for _, payment in self.scheduled_payments.items():
            if payment.account_id == account_id_2:
                payment.account_id = account_id_1
        self.audit[account_id_1].append((timestamp, target.amount))
        self.audit[account_id_2].append((timestamp, None))

        del self.transfers[account_id_2]
        del self.bank[account_id_2]
        return True

    def get_balance(self, timestamp, account_id, time_at) -> int | None:
        self._execute_scheduled_payments(timestamp)
        
        audits = self.audit.get(account_id, [])

        entries_before_at = bisect_right(audits, time_at, key= lambda entry: entry[0]) -1

        if entries_before_at < 0: return None

        return audits[entries_before_at][1]
