import os

from dotenv import load_dotenv

from browser_use import Agent, ChatOpenAI

load_dotenv()
import asyncio

# get an api key from https://modelstudio.console.alibabacloud.com/?tab=playground#/api-key
api_key = "sk-be41959674154c7890f354538eed65f6"
base_url = 'https://dashscope.aliyuncs.com/compatible-mode/v1'

project_api_key = os.getenv('LMNR_PROJECT_API_KEY')
if project_api_key:
	from lmnr import Laminar
	Laminar.initialize(project_api_key=project_api_key)
# so far we only had success with qwen-vl-max
# other models, even qwen-max, do not return the right output format. They confuse the action schema.
# E.g. they return actions: [{"navigate": "google.com"}] instead of [{"navigate": {"url": "google.com"}}]
# If you want to use smaller models and you see they mix up the action schema, add concrete examples to your prompt of the right format.
llm = ChatOpenAI(model='qwen-vl-max', api_key=api_key, base_url=base_url)


async def main():
	agent = Agent(task='打开优酷视频(https://www.youku.com/ku/webhome)搜索黑夜告白播放第三集', llm=llm, use_vision=True, max_actions_per_step=1)
	await agent.run()


if '__main__' == __name__:
	asyncio.run(main())
