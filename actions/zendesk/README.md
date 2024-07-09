# Zendesk

Action Package interacting with Zendesk resources.

Possible actions with this package are:

- search for the tickets based on different attributes such as status, description, assignee, etc
- get the ticket comments
- assign a ticket to a user or a group
- update the status of the ticket

## Prompts

```
Give me all the tickets that match the word "Gift".
```

> Here are the tickets that match the word "Gift":
>
> 1. Ticket ID: 25
>    * Subject: SAMPLE TICKET: Gift card expiring
>    * Description: Hey there, I was lucky enough to receive a gift card from a friend as a housewarming gift. Small problem, I’ve been so swamped with the move I totally forgot about it until now and it expires in a week! Can you extend the expiration date? Help, Luka Jensen
>    * Status: Closed
>    * Priority: Normal
>    * Tags: gift_cards, sample_ticket
>    * Requester: Luka Jensen
> 2. Ticket ID: 24
>    * Subject: SAMPLE TICKET: Gift card
>    * Description: Hi there, I have a friend who recently moved overseas and I was thinking of sending her a housewarming gift. I saw that you offer international gift cards, but I’m a little unsure about how the whole process works. Could you explain? Like what the denominations are, how we determine the recipient’s currency, and how to personalize the gift card? Cheers, Blake Jackson
>    * Status: Open
>    * Priority: Normal
>    * Tags: gift_cards, sample_ticket
>    * Requester: Blake Jackson

```
Give me all the closed tickets that have the contains the word "expires".
```

> Here are the tickets that match the word "Gift":
>
> 1. Ticket ID: 25
>    * Subject: SAMPLE TICKET: Gift card expiring
>    * Description: Hey there, I was lucky enough to receive a gift card from a friend as a housewarming gift. Small problem, I’ve been so swamped with the move I totally forgot about it until now and it expires in a week! Can you extend the expiration date? Help, Luka Jensen
>    * Status: Closed
>    * Priority: Normal
>    * Tags: gift_cards, sample_ticket
>    * Requester: Luka Jensen

```
Give me all the comments for this ticket "Gift card expiring" ticket.
```

> Here are the comments for the ticket titled "SAMPLE TICKET: Gift card expiring":
> 
> 1. Comment by Luka Jensen (Requester)
>   * Date: 2024-06-24
>   * Content: Hey there, I was lucky enough to receive a gift card from a friend as a housewarming gift. Small problem, I’ve been so swamped with the move I totally forgot about it until now and it expires in a week! Can you extend the expiration date? Help, Luka Jensen
> 2. Comment by Ovidiu Rusu (Agent)
>    * Date: 2024-06-24
>    * Content: No problem, we are going to extend the expiration date with 1 month!

> These comments reflect the initial request for extending the expiration date of a gift card and the agent's confirmation of resolving the issue. If you need further details or actions on this ticket, please let me know!

```
Assign the ticket 25 to the Priority group
```

> The ticket with ID 25 has been successfully assigned to the Priority group.



## Authorization

This action package uses OAuth2 flow to authenticate user.

Scopes in use:
    
    - read
    - tickets:write