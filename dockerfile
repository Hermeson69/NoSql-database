FROM cassandra:5.0

ENV CASSANDRA_CLUSTER_NAME="cluster" \
    CASSANDRA_DC="dc1" \
    CASSANDRA_RACK="rack1" \
    CASSANDRA_ENDPOINT_SNITCH="GossipingPropertyFileSnitch" \
    MAX_HEAP_SIZE="1G" \
    HEAP_NEWSIZE="256M" \
    JVM_EXTRA_OPTS="-XX:+UseG1GC -XX:MaxGCPauseMillis=200 -XX:+AlwaysPreTouch -Dcassandra.skip_wait_for_gossip_to_settle=0"


VOLUME /var/lib/cassandra

EXPOSE 9042 

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=5 \
    CMD cqlsh -u cassandra -p cassandra localhost 9042 -e "SELECT cluster_name FROM system.local" >/dev/null 2>&1 || exit 1

USER cassandra