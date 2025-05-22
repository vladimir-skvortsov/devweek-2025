import json
import os
import uuid
from typing import Dict, List, Optional

from dotenv import load_dotenv
from pyairtable import Table

load_dotenv()


class AirtableClient:
    def __init__(self):
        self.token = os.getenv('AIRTABLE_TOKEN')
        self.base_id = 'appBdrOMH7UmeXVyA'
        self.records_table = Table(self.token, self.base_id, 'Records')
        self.users_table = Table(self.token, self.base_id, 'Users')
        self.links_table = Table(self.token, self.base_id, 'Links')

    def create_user(self, tg_id: Optional[str], login: Optional[str], password: Optional[str]) -> Dict:
        data = {}
        if tg_id:
            data['tg_id'] = tg_id
        if login:
            data['login'] = login
        if password:
            data['password'] = password
        data['user_id'] = uuid.uuid4().hex
        return self.users_table.create(data)

    def get_user_id_by_tg_id(self, tg_id: str) -> Optional[str]:
        users = self.users_table.all()
        for user in users:
            fields = user.get('fields', {})
            if fields.get('tg_id') == tg_id:
                return fields.get('user_id')
        return None

    def create_record(
        self, text: str, tokens: List[Dict[str, float]], explanation: str, score: float, examples: str
    ) -> Dict:
        data = {
            'record_id': uuid.uuid4().hex,
            'text': text,
            'tokens': json.dumps(tokens),
            'explanation': explanation,
            'score': str(score),
            'examples': examples,
        }
        return self.records_table.create(data)

    def link_user_to_record(self, user_id: str, record_id: str) -> Dict:
        data = {
            'user_id': user_id,
            'record_id': record_id,
        }
        return self.links_table.create(data)

    def get_record_by_id(self, record_id: str) -> Optional[Dict]:
        records = self.records_table.all()
        for record in records:
            if record['fields'].get('record_id') == record_id:
                return self._normalize_record(record)
        return None

    def get_last_record(self) -> Optional[Dict]:
        records = self.records_table.all(sort=['-record_id'])
        if records:
            return self._normalize_record(records[0])
        return None

    def get_last_record_by_tg_id(self, tg_id: str) -> Optional[Dict]:
        user_id = self.get_user_id_by_tg_id(tg_id)
        if not user_id:
            return None
        links = self.links_table.all()
        record_ids = [link['fields']['record_id'] for link in links if link['fields'].get('user_id') == user_id]
        if not record_ids:
            return None
        records = self.records_table.all()
        user_records = [r for r in records if r['fields'].get('record_id') in record_ids]
        user_records.sort(key=lambda r: r['fields'].get('record_id', ''), reverse=True)
        if user_records:
            return self._normalize_record(user_records[0])
        return None

    def _normalize_record(self, record: Dict) -> Dict:
        fields = record.get('fields', {})
        result = {
            'record_id': fields.get('record_id'),
            'text': fields.get('text'),
            'explanation': fields.get('explanation'),
            'score': float(fields.get('score', 0.0)),
            'tokens': json.loads(fields.get('tokens', '[]')),
            'examples': fields.get('examples'),
        }
        return result
