# HubSpot

Action Package interacting with HubSpot resources.

It is currently capable of searching for and retrieving CRM objects like companies, contacts, deals etc. The search is relying on a basic query string matched against all the properties, while the returned results can be limited.

## Prompts

```
Hey, please tell me what companies we have in HubSpot matching "AI".
```

> Here are the companies in HubSpot matching "AI":
> 1. Fireflies.ai
> 2. substorm.ai
> 3. sp.ai

```
Now, please give me a contact for the first company listed previously.
```

> The contact for Fireflies.ai listed in HubSpot is:
>
> * Name: Fireflies.ai Notetaker
> * Email: fred@fireflies.ai

```
Show me the tasks in HubSpot matching "prebuilt" and list them by priority please.
```

> I found 2 tasks in HubSpot matching "prebuilt" and here they are listed by priority:
>
> 1. Prebuilt Actions - README test
>    * Priority: HIGH
>    * Status: NOT_STARTED
>    * Type: TODO
>    * Created Date: 2024-05-08
>    * Description: This is high prio!
> 2. Prebuilt Action task
>    * Priority: MEDIUM
>    * Status: NOT_STARTED
>    * Type: CALL
>    * Created Date: 2024-04-29
>    * Description: Hey, please take this task and sort it out so it is shown in our Prebuilt Action searching capability.

## Caveats

- The search is quite basic, not supporting yet complex queries, nor filtering and sorting the results.
- The set of actions is currently limited to read-only operations, although it's on the roadmap to enable a broader use, like creating/updating and deleting objects as well.
- The actions are currently supporting the following object types only:
  - CRM: companies, contacts, deals, tickets, tasks
