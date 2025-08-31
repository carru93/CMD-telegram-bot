# Community Manager Defender Bot
Community Manager Defender Bot is a simple, open-source Telegram bot that you can self-host on your own AWS account at little to no cost.

Once you complete the steps in the Get Started section, you can add the bot to any group and assign it as an administrator with permission to restrict members. From there, the bot will help you automatically moderate new users — giving you more peace of mind and a quieter community.

# Requirements

* [AWS CLI configured](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)
* [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)

# Get Started

1. Obtain a token for your new bot from **BotFather** using the `/newbot` command.
2. Create the `.env` file from the template, setting `AWS_PROFILE` and the `BOT_TOKEN` you just received.
3. Deploy with:

   ```bash
   ./deploy
   ```
4. Set the Telegram webhook to the newly created **API Gateway** endpoint. Replace placeholders and run:

   ```bash
   curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     --data-urlencode "url=<API_GATEWAY_ENDPOINT>" \
     --data-urlencode 'allowed_updates=["message","callback_query"]' \
     --data-urlencode "drop_pending_updates=true"
   ```

   You should receive a JSON response like:

   ```json
   {"ok":true,"result":true,"description":"Webhook was set"}
   ```

   You can also do everythin in your browser and put the following url in the search bar:
   ```bash
   "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url={API_GATEWAY_ENDPOINT}"
   ```
   but with this GET call you cannot limit the type of events you will get.

> **Important:** copy the endpoint **exactly** and **do not** add a trailing slash. For HTTP APIs the route is `/webhook` (e.g., `https://<api-id>.execute-api.<region>.amazonaws.com/webhook`).
