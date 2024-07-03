# vtds-application-demo

A simple demo application layer for vTDS. This sets up a cluster
consisting of Virtual Networks, one containing "non-SCS" and "SCS"
Virtual Nodes the other containing "non-FSM" and "FSM" virtual nodes
and a third network connecting the SCS nodes to the FSM nodes. The
non-SCS nodes should not be able to see the non-FSM or FSM nodes and
the non-FSM nodes should not be able to see the non-SCS or SCS nodes,
but the FSM and SCS nodes should be able to talk to each other freely.
