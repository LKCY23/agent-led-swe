"""Inspect the reference patch against the published None-filtering requirement."""
import asyncio
import json
from types import SimpleNamespace

from agents.model_settings import ModelSettings
from agents.models.interface import ModelTracing
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel


class Captured(Exception):
    pass


async def main():
    captured = {}

    async def create(**kwargs):
        captured.update(kwargs)
        raise Captured

    client = SimpleNamespace(base_url='https://unused.invalid',
                             chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    model = OpenAIChatCompletionsModel(model='mock-only', openai_client=client)
    try:
        await model.get_response(system_instructions=None, input='test',
            model_settings=ModelSettings(extra_args={'probe_null': None, 'probe_value': 7}),
            tools=[], output_schema=None, handoffs=[], tracing=ModelTracing.DISABLED,
            previous_response_id=None)
    except Captured:
        pass
    assert captured, 'Did not reach the mock client'
    print(json.dumps({'reference_null_filtered': 'probe_null' not in captured,
                      'reference_non_null_forwarded': captured.get('probe_value') == 7}))


asyncio.run(main())
