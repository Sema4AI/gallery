# HubSpot

Action Package interacting with HubSpot resources.

The system supports comprehensive management of CRM objects, including companies, contacts, deals, and more. Key functionalities include:

### Search and Retrieval

- **Basic Search**: Perform searches using a basic query string matched against all properties.
- **Advanced Filters**: Apply advanced filters to refine search results.
- **Result Limiting**: Limit the number of returned results for efficiency.

### CRUD Operations

- **Create**: Add new CRM objects effortlessly.
- **Update**: Modify existing CRM objects with ease.
- **Delete**: Remove CRM objects when no longer needed.

These capabilities ensure efficient and flexible management of CRM data, allowing for tailored searches and seamless object manipulation.

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


```
Give me all the companies created in the past 10 days.
```

> Here are the companies created in the past 10 days:
>
> 1. Avamm
>    * Domain: avamm.com
>    * ID: 12337834190
> 2. Youbridge
>    * Domain: youbridge.com
>    * ID: 12338224068


```
Give me all the tickets that were modified in the past 10 days.
```

> Here is the ticket that was modified in the past 15 days:
>
> 1. Test-Ticket
>    * Content: Testing modified content
>    * Created Date: July 17, 2024
>    * Priority: LOW
>    * Pipeline Stage: 1
>    * ID: 3613848566

```
Create a new Ticket to address the delivery issues for Jaloo, set the priority as Medium and add it to Support.
```

> A new ticket has been successfully created to address the delivery issues for Jaloo. Here are the details:
> 
> * Subject: Delivery Issues for Jaloo
> * Content: Addressing the delivery issues for Jaloo.
> * Priority: MEDIUM
> * Pipeline Stage: New
> * Ticket ID: 3613292501

```
Assign the Delivery Issues for Jaloo ticket to Tommi and make it high priority.
```

> The ticket Ovidiu-Test-Ticket1 has been successfully updated:
>
> Priority: HIGH
> Assigned to: Tommi
