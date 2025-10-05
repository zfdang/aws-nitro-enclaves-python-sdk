from cffi import FFI

ffibuilder = FFI()

ffibuilder.cdef(
    """
    typedef struct {
        int closed;
        char module_id[33];
        unsigned char pcrs[32][32];
        unsigned char pcr_locks[32];
        unsigned char *cert_data[4];
        size_t cert_len[4];
    } nsm_session;

    nsm_session *nsm_session_new(void);
    void nsm_session_free(nsm_session *session);
    int nsm_session_is_closed(const nsm_session *session);
    int nsm_session_close(nsm_session *session);

    const char *nsm_module_id(const nsm_session *session);

    int nsm_get_random(nsm_session *session, unsigned char *out, size_t length);
    int nsm_describe_pcr(const nsm_session *session, uint32_t slot, unsigned char *out);
    int nsm_extend_pcr(nsm_session *session, uint32_t slot, const unsigned char *data, size_t length, unsigned char *out);
    int nsm_lock_pcr(nsm_session *session, uint32_t slot);
    int nsm_lock_range(nsm_session *session, uint32_t limit);

    int nsm_set_certificate(nsm_session *session, uint32_t slot, const unsigned char *data, size_t length);
    int nsm_describe_certificate(const nsm_session *session, uint32_t slot, const unsigned char **out, size_t *length);
    int nsm_remove_certificate(nsm_session *session, uint32_t slot);

    int nsm_attestation_digest(const nsm_session *session, unsigned char *digest_out);
    int nsm_locked_flags(const nsm_session *session, unsigned char *flags_out, size_t length);

    #define NSM_OK 0
    #define NSM_ERR_INVALID_SLOT 1
    #define NSM_ERR_LOCKED 2
    #define NSM_ERR_INVALID_LENGTH 3
    #define NSM_ERR_CERT_MISSING 4
    #define NSM_ERR_NO_MEMORY 5
    #define NSM_ERR_CLOSED 6
    """
)

ffibuilder.set_source(
    "aws_nitro_enclaves.nsm._native",
    None,
    sources=["aws_nitro_enclaves/nsm/_native.c"],
    include_dirs=[],
)

if __name__ == "__main__":  # pragma: no cover - manual build hook
    ffibuilder.compile(verbose=True)
