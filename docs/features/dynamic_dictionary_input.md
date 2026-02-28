# Dynamic Dictionary Input

## Problem

Pydantic models does not support free-form dictionary keys.

The solution works by creating a temporary, invisible "bridge" when PICLE encounters a Python Dictionary field `(Dict[...])`.

Here is the simple breakdown.

## 1. The "Bridge" (VirtualDictModel)

Normally, PICLE looks for exact matches of field names in your Pydantic model. However, a dictionary implies that you get to invent the key name (like name1 or my_entry) at runtime. PICLE cannot know this name in advance.

When PICLE sees a field like `mytopkey: Dict[str, MyNestedModel]`, it creates a special `VirtualDictModel`. Think of this as a placeholder that says: "I am waiting for one word to serve as the dictionary key."

## 2. How it flows step-by-step

When you type the command: picle# mytopkey name1 k1 v1

mytopkey: PICLE finds this field in your root model. It sees it is a Dict. It switches to the "Bridge" mode.
name1: PICLE expects a key here. It grabs "name1" and says, "Okay, this is the key for our dictionary."
Transition: PICLE looks at the dictionary definition (Dict[..., MyNestedModel]). It knows that whatever is under this key must look like MyNestedModel.

k1 v1: PICLE now switches to MyNestedModel and parses k1 v1 just like normal fields.

## 3. Reconstructing the Data

At the end, PICLE takes these three pieces—the field name (mytopkey), the captured key (name1), and the nested data ({'k1': 'v1'})—and stitches them together into the final nested structure:

## 4. Customizing Help

To make the "Bridge" user-friendly, we look at json_schema_extra keys (pkey and pkey_description).

Instead of showing nothing, PICLE uses these to tell the user: <name> Input name when they ask for help (?).
This allows you to mix structured, strict Pydantic models with free-form dictionary keys seamlessly.