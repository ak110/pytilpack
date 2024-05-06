#!/bin/bash
set -eux
#
# OpenAI APIを用いたテストデータ作成用ツール。
# 環境変数 OPENAI_API_KEY が定義済みの状態で実行する。(有料)
#
curl -i -o openai.chat.function1.txt https://api.openai.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
   "model":"gpt-3.5-turbo",
   "messages":[
      {
         "role":"user",
         "content":"1+1=?"
      }
   ],
   "tool_choice":"auto",
   "tools":[
      {
         "type":"function",
         "function":{
            "name":"calculator",
            "description":"calculate the result of a mathematical expression",
            "parameters":{
               "type":"object",
               "properties":{
                  "expression":{
                     "type":"string",
                     "description":"the mathematical expression to calculate"
                  }
               },
               "required":[
                  "expression"
               ]
            }
         }
      }
   ],
   "stream":true
}'
