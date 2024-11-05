# ServiceNow

Action Package interacting with A ServiceNow instance 

The package is able to read incidents and list of the users.


## Prompts

```
Search all recent incidents
```

> There are no incidents that have been created today. If you have any other questions or need further assistance, feel free to let me know!


```
Do I have any openend incidents?
```

> You have the following open incident:
> * Incident Number: INC0009009
> * State: In Progress
> * Priority: 4 - Low
> * Short Description: Unable to access the shared folder.
> * Opened By: System Administrator
> * Assigned To: System Administrator
> * Assignment Group: Team Development Code Reviewers
> * Description: Unable to access the shared folder. Please provide access.
> * Urgency: 2 - Medium  
>
> If you need more details or further assistance, feel free to ask!

```
Can you count all the incidents created in the last 10 years
```

> There are more than 20 incidents created in the last 10 years. The list I retrieved is just a partial result, showing the first 20 incidents. If you need the exact count or more details, please let me know, and I can continue retrieving more data.

``` 
Yes I need the exact count
```

> There are 30 incidents created in the last 10 years. If you need more information or further assistance, feel free to ask!


## Authorization

This action package uses the username and password of the user to authenticate against the ServiceNow instance.