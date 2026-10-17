c-----------------------------------------------------------------------
      program p7f_drydep_oracle
c-----------------------------------------------------------------------
c
c --- CTEAS P7F FORTRAN ORACLE DRIVER -- hand written for this test
c     harness. This file is NOT vendor source and is never used by the
c     model; it drives the UNMODIFIED vendor unit VDCOMP (extracted by
c     reference/drydep_source_anchor.py) so the P7F C++ dry deposition
c     resistance model can be compared with the original algorithm.
c
c --- The time-invariant /DRYGAS/ parameters are prepared here exactly as
c     the vendor DRYI does them (calpuff.for DRYI L26980-27035):
c       pdiff(i) = pdiff(i)*1.e-4          (cm**2/s -> m**2/s)
c       rm(i)    = rm(i)*1.e2              (s/cm -> s/m)
c       rcutr    = rcutr*1.e2 ; rgr = rgr*1.e2
c       sc  = vair/pdiff(i)  with vair = 0.15e-4 m**2/s
c       rd1(i)  = dconst1*sc**dconst2/vk
c       rcut(i) = rcutr*(reactr/react(i))
c       rgg(i)  = rgr*(reactr/react(i))
c       rgw1(i) = henry(i)/(alphas(i)*dconst3)
c     DRYI itself cannot be linked here because it calls RDVD, which
c     references the vendor input reader; the formulas above are quoted
c     from it and are verified against the vendor text by CTest.
c
c --- Input on stdin:
c     line 1 (once, DRYI reference values):
c        rcutr rgr reactr dconst1 dconst2 dconst3 pconst bmin bmax qswmax
c     line 2 (once): nspec
c     next nspec lines: idryflg pdiff_cm2s alpha react rm_s_cm henry
c     then one line per case:
c        icase iveg u10 v10 ilu iwat1 iwat2 z0 tdegk ustar el xlai qsw zref
c     Output per case:
c        icase vd(1..nspec)
c-----------------------------------------------------------------------
      include 'params.puf'
      include 'drygas.puf'
      include 'drydep.puf'
      include 'drypart.puf'
c
      integer icase,ios,ilu,iwat1,iwat2,nspecin
      integer idryin(mxspec)
      real vdin(mxspec)
      real pdiffin(mxspec),alphain(mxspec),reactin(mxspec)
      real rmin(mxspec),henryin(mxspec)
      real u10,v10,z0,tdegk,ustar,el,xlai,qsw
      real dumlid,dumstep,dummixh,dumwstar
      logical ldb
c
c --- IDRYFLG, VDUSER, ZREF and IVEG are declared in /DRYDEP/ (drydep.puf);
c     the /DRYGAS/ reference values are read straight into the common block.
      real vairm,vkm
      data vairm/0.15e-4/,vkm/0.4/
c
      ldb=.false.
      read(*,*,iostat=ios) rcutr,rgr,reactr,dconst1,dconst2,dconst3,
     &                     pconst,bmin,bmax,qswmax
      if(ios.ne.0) stop 'P7F oracle: missing setup line'
      read(*,*,iostat=ios) nspecin
      if(ios.ne.0) stop 'P7F oracle: missing species count'
      nspec=nspecin
      do 10 j=1,nspec
         read(*,*,iostat=ios) idryin(j),pdiffin(j),alphain(j),
     &        reactin(j),rmin(j),henryin(j)
         if(ios.ne.0) stop 'P7F oracle: missing species line'
10    continue
      do 11 j=1,mxspec
      do 11 n=1,24
         vduser(n,j)=0.0
11    continue
c
20    continue
c ---    The last four fields (lid height, sampling step, mixing height,
c        w*) belong to the DRY removal branch, which VDCOMP does not use;
c        they are read to keep both harnesses on one line protocol.
      read(*,*,iostat=ios) icase,iveg,u10,v10,ilu,iwat1,iwat2,z0,tdegk,
     &                     ustar,el,xlai,qsw,zref,dumlid,dumstep,dummixh,
     &                     dumwstar
      if(ios.ne.0) goto 999
c
c ---    DRYI equivalents for this case
         do 30 j=1,nspec
            idryflg(j)=idryin(j)
            vdin(j)=0.0
            if(idryin(j).eq.1 .or. idryin(j).eq.2)then
               pdiff(j)=pdiffin(j)*1.e-4
               rm(j)=rmin(j)*1.e2
            else
               pdiff(j)=pdiffin(j)
               rm(j)=rmin(j)
            endif
            alphas(j)=alphain(j)
            react(j)=reactin(j)
            henry(j)=henryin(j)
30       continue
         do 40 j=1,nspec
            if(idryin(j).ne.1 .and. idryin(j).ne.2) goto 40
            sc=vairm/pdiff(j)
            rd1(j)=dconst1*sc**dconst2/vkm
            ratio=reactr/react(j)
            rcut(j)=rcutr*ratio
            rgg(j)=rgr*ratio
            rgw1(j)=henry(j)/(alphas(j)*dconst3)
40       continue
c
         call vdcomp(idryflg,nspec,zref,iveg,u10,v10,ilu,iwat1,iwat2,
     &        z0,tdegk,ustar,el,xlai,qsw,vduser,1,ldb,vdin)
         do 50 j=1,nspec
            write(*,'(i8,1x,i4,1x,es18.10)') icase,j,vdin(j)
50       continue
      goto 20
c
999   continue
      end
