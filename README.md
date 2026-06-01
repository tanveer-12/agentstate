# agentstate
Building a stateful coordination layer for multi-agent AI systems.

Right now, most multi-agent AI systems just use a giant chat history or a messy dictionary to share information between agents. That makes them fragile: agents overwrite each other, there’s no clear picture of what the ‘world’ looks like, and you can’t see who changed what or rewind if something goes wrong.

I’m building a Python library that fixes this by giving agents a shared, structured world to operate in. Agents don’t directly change the state; they propose small, structured updates that my library validates, logs, and applies. Every change is saved as an event, so you can replay the whole run, debug it, and recover from failures. On top of that, there’s a graph that decides which agent runs next based on the current state, plus tooling to see what’s happening in real time. It doesn’t talk to models or handle prompts; it just manages state, coordination, and observability for multi-agent systems.
