/* Auto-extracted C implementation for the NSM CFFI shim. */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define PCR_SLOTS 32
#define PCR_DIGEST_LEN 32
#define CERT_SLOTS 4

#define MODULE_ID_LEN 33

#define NSM_OK 0
#define NSM_ERR_INVALID_SLOT 1
#define NSM_ERR_LOCKED 2
#define NSM_ERR_INVALID_LENGTH 3
#define NSM_ERR_CERT_MISSING 4
#define NSM_ERR_NO_MEMORY 5
#define NSM_ERR_CLOSED 6

typedef struct {
    int closed;
    char module_id[MODULE_ID_LEN];
    unsigned char pcrs[PCR_SLOTS][PCR_DIGEST_LEN];
    unsigned char pcr_locks[PCR_SLOTS];
    unsigned char *cert_data[CERT_SLOTS];
    size_t cert_len[CERT_SLOTS];
} nsm_session;

static int random_seeded = 0;

static void seed_random(void) {
    if (!random_seeded) {
        srand((unsigned int)time(NULL));
        random_seeded = 1;
    }
}

static void random_bytes(unsigned char *out, size_t length) {
    seed_random();
    for (size_t i = 0; i < length; ++i) {
        out[i] = (unsigned char)(rand() % 256);
    }
}

static void make_module_id(char *buffer) {
    unsigned char raw[16];
    random_bytes(raw, sizeof(raw));
    const char *hex = "0123456789abcdef";
    for (size_t i = 0; i < sizeof(raw); ++i) {
        buffer[i * 2] = hex[raw[i] >> 4];
        buffer[i * 2 + 1] = hex[raw[i] & 0x0F];
    }
    buffer[32] = '\0';
}

static void simple_hash(const unsigned char *data, size_t length, unsigned char out[PCR_DIGEST_LEN]) {
    unsigned char acc = 0x42;
    for (size_t i = 0; i < PCR_DIGEST_LEN; ++i) {
        unsigned char value = (unsigned char)(acc + (unsigned char)i * 17u);
        for (size_t j = i; j < length; j += PCR_DIGEST_LEN) {
            value = (unsigned char)((value << 5) | (value >> 3));
            value ^= data[j];
        }
        out[i] = value ^ (unsigned char)(length & 0xFFu);
    }
}

nsm_session *nsm_session_new(void) {
    nsm_session *session = (nsm_session *)calloc(1, sizeof(nsm_session));
    if (!session) {
        return NULL;
    }
    make_module_id(session->module_id);
    for (size_t i = 0; i < PCR_SLOTS; ++i) {
        memset(session->pcrs[i], 0, PCR_DIGEST_LEN);
        session->pcr_locks[i] = 0;
    }
    for (size_t i = 0; i < CERT_SLOTS; ++i) {
        session->cert_data[i] = NULL;
        session->cert_len[i] = 0;
    }
    session->closed = 0;
    return session;
}

void nsm_session_free(nsm_session *session) {
    if (!session) {
        return;
    }
    for (size_t i = 0; i < CERT_SLOTS; ++i) {
        if (session->cert_data[i]) {
            free(session->cert_data[i]);
        }
    }
    free(session);
}

static int ensure_open(const nsm_session *session) {
    if (!session || session->closed) {
        return NSM_ERR_CLOSED;
    }
    return NSM_OK;
}

int nsm_session_is_closed(const nsm_session *session) {
    if (!session) {
        return 1;
    }
    return session->closed ? 1 : 0;
}

int nsm_session_close(nsm_session *session) {
    if (!session) {
        return NSM_ERR_CLOSED;
    }
    session->closed = 1;
    return NSM_OK;
}

const char *nsm_module_id(const nsm_session *session) {
    if (!session) {
        return NULL;
    }
    return session->module_id;
}

static int validate_slot(uint32_t slot) {
    if (slot >= PCR_SLOTS) {
        return NSM_ERR_INVALID_SLOT;
    }
    return NSM_OK;
}

int nsm_get_random(nsm_session *session, unsigned char *out, size_t length) {
    if (ensure_open(session) != NSM_OK) {
        return NSM_ERR_CLOSED;
    }
    if (!out || length == 0) {
        return NSM_ERR_INVALID_LENGTH;
    }
    random_bytes(out, length);
    return NSM_OK;
}

int nsm_describe_pcr(const nsm_session *session, uint32_t slot, unsigned char *out) {
    if (ensure_open(session) != NSM_OK) {
        return NSM_ERR_CLOSED;
    }
    if (validate_slot(slot) != NSM_OK) {
        return NSM_ERR_INVALID_SLOT;
    }
    memcpy(out, session->pcrs[slot], PCR_DIGEST_LEN);
    return NSM_OK;
}

int nsm_extend_pcr(nsm_session *session, uint32_t slot, const unsigned char *data, size_t length, unsigned char *out) {
    if (ensure_open(session) != NSM_OK) {
        return NSM_ERR_CLOSED;
    }
    if (validate_slot(slot) != NSM_OK) {
        return NSM_ERR_INVALID_SLOT;
    }
    if (!data || length == 0) {
        return NSM_ERR_INVALID_LENGTH;
    }
    if (session->pcr_locks[slot]) {
        return NSM_ERR_LOCKED;
    }
    unsigned char *buffer = (unsigned char *)malloc(PCR_DIGEST_LEN + length);
    if (!buffer) {
        return NSM_ERR_NO_MEMORY;
    }
    memcpy(buffer, session->pcrs[slot], PCR_DIGEST_LEN);
    memcpy(buffer + PCR_DIGEST_LEN, data, length);
    simple_hash(buffer, PCR_DIGEST_LEN + length, session->pcrs[slot]);
    memcpy(out, session->pcrs[slot], PCR_DIGEST_LEN);
    free(buffer);
    return NSM_OK;
}

int nsm_lock_pcr(nsm_session *session, uint32_t slot) {
    if (ensure_open(session) != NSM_OK) {
        return NSM_ERR_CLOSED;
    }
    if (validate_slot(slot) != NSM_OK) {
        return NSM_ERR_INVALID_SLOT;
    }
    session->pcr_locks[slot] = 1;
    return NSM_OK;
}

int nsm_lock_range(nsm_session *session, uint32_t limit) {
    if (ensure_open(session) != NSM_OK) {
        return NSM_ERR_CLOSED;
    }
    if (limit > PCR_SLOTS) {
        limit = PCR_SLOTS;
    }
    for (uint32_t i = 0; i < limit; ++i) {
        session->pcr_locks[i] = 1;
    }
    return NSM_OK;
}

int nsm_set_certificate(nsm_session *session, uint32_t slot, const unsigned char *data, size_t length) {
    if (ensure_open(session) != NSM_OK) {
        return NSM_ERR_CLOSED;
    }
    if (slot >= CERT_SLOTS) {
        return NSM_ERR_INVALID_SLOT;
    }
    if (!data || length == 0) {
        return NSM_ERR_INVALID_LENGTH;
    }
    unsigned char *copy = (unsigned char *)malloc(length);
    if (!copy) {
        return NSM_ERR_NO_MEMORY;
    }
    memcpy(copy, data, length);
    if (session->cert_data[slot]) {
        free(session->cert_data[slot]);
    }
    session->cert_data[slot] = copy;
    session->cert_len[slot] = length;
    return NSM_OK;
}

int nsm_describe_certificate(const nsm_session *session, uint32_t slot, const unsigned char **out, size_t *length) {
    if (ensure_open(session) != NSM_OK) {
        return NSM_ERR_CLOSED;
    }
    if (slot >= CERT_SLOTS) {
        return NSM_ERR_INVALID_SLOT;
    }
    if (!session->cert_data[slot]) {
        return NSM_ERR_CERT_MISSING;
    }
    *out = session->cert_data[slot];
    *length = session->cert_len[slot];
    return NSM_OK;
}

int nsm_remove_certificate(nsm_session *session, uint32_t slot) {
    if (ensure_open(session) != NSM_OK) {
        return NSM_ERR_CLOSED;
    }
    if (slot >= CERT_SLOTS) {
        return NSM_ERR_INVALID_SLOT;
    }
    if (!session->cert_data[slot]) {
        return NSM_ERR_CERT_MISSING;
    }
    free(session->cert_data[slot]);
    session->cert_data[slot] = NULL;
    session->cert_len[slot] = 0;
    return NSM_OK;
}

int nsm_attestation_digest(const nsm_session *session, unsigned char *digest_out) {
    if (ensure_open(session) != NSM_OK) {
        return NSM_ERR_CLOSED;
    }
    unsigned char buffer[PCR_SLOTS * PCR_DIGEST_LEN];
    for (size_t i = 0; i < PCR_SLOTS; ++i) {
        memcpy(buffer + (i * PCR_DIGEST_LEN), session->pcrs[i], PCR_DIGEST_LEN);
    }
    simple_hash(buffer, sizeof(buffer), digest_out);
    return NSM_OK;
}

int nsm_locked_flags(const nsm_session *session, unsigned char *flags_out, size_t length) {
    if (ensure_open(session) != NSM_OK) {
        return NSM_ERR_CLOSED;
    }
    size_t copy = length < PCR_SLOTS ? length : PCR_SLOTS;
    memcpy(flags_out, session->pcr_locks, copy);
    if (copy < length) {
        memset(flags_out + copy, 0, length - copy);
    }
    return NSM_OK;
}
